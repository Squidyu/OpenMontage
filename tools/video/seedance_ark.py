"""Seedance 1.5 / 2.0 (ByteDance) video generation via Volcengine ARK gateway.

Direct access through the Volcengine ARK (方舟) gateway. Uses a simple Bearer
API key (ARK_API_KEY) -- no SigV4 signing required. This is the working path
for personal Volcengine accounts.

=== SETUP ===

Get a free API key + model endpoint at https://console.volcengine.com/ark
(you can apply for the Seedance 1.5 trial). Then set in .env:

  ARK_API_KEY=ark-xxxx-xxxx
  ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
  SEEDANCE_MODEL=doubao-seedance-1-5-pro-251215

All three can also be passed per-call in `inputs` to override the env values.

=== API SHAPE (verified against volcenginesdkarkruntime) ===

  POST {ARK_BASE_URL}/contents/generations/tasks        (Bearer auth)
    { "model": ..., "content": [{"type":"text","text":...}], ... }
  -> { "id": "cgt-2026..." }

  GET  {ARK_BASE_URL}/contents/generations/tasks/{id}
  -> { "status": "succeeded",
       "content": {"video_url": "...", "last_frame_url": "...", "file_url": "..."},
       "seed": ..., "duration": ..., "ratio": ..., "revised_prompt": ... }

Pricing: billed per second of generated video. Seedance 1.5/2.0 are roughly
~¥1/sec (≈$0.14/sec); override with SEEDANCE_COST_PER_SEC if your rate differs.
Note: the generated video_url is a TOS signed URL valid 24h, so it is downloaded
immediately.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class SeedanceARK(BaseTool):
    name = "seedance_ark"
    version = "0.3.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "seedance"
    stability = ToolStability.BETA  # Verified end-to-end against live ARK gateway
    execution_mode = ExecutionMode.ASYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Volcengine ARK gateway for Seedance (1.5 / 2.0).\n\n"
        "  1. Open https://console.volcengine.com/ark\n"
        "  2. Apply for / create a Seedance model endpoint (e.g. doubao-seedance-1-5-pro-251215)\n"
        "  3. Create an API key and copy it\n"
        "  4. Set in .env:\n"
        "       ARK_API_KEY=ark-xxxx\n"
        "       ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3\n"
        "       SEEDANCE_MODEL=doubao-seedance-1-5-pro-251215\n"
        "Pricing: billed per output second (~¥1/sec for 2.0; override SEEDANCE_COST_PER_SEC)."
    )
    agent_skills = ["seedance-2-0", "ai-video-gen"]

    capabilities = ["text_to_video", "image_to_video", "reference_to_video"]
    supports = {
        "text_to_video": True,
        "image_to_video": True,
        "reference_to_video": True,
        "multiple_reference_images": True,
        "reference_image": True,
        "native_audio": True,
        "cinematic_quality": True,
        "camera_direction": True,
        "lip_sync": True,
        "multi_shot": True,
        "aspect_ratio": True,
        "seed": True,
    }
    best_for = [
        "personal Volcengine accounts (simple Bearer API key, no SigV4)",
        "cheapest practical Seedance access -- direct ARK gateway, no fal.ai markup",
        "cinematic trailers, teasers, and premium clips at ~$0.14/sec",
        "director-level camera control and multi-shot editing",
        "reference-conditioned generation with character identity lock",
    ]
    not_good_for = [
        "offline generation",
    ]
    fallback_tools = ["seedance_video", "seedance_replicate", "veo_video"]
    quality_score = 0.93  # 1.5 Pro slightly under 2.0's 0.95

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video", "reference_to_video"],
                "default": "text_to_video",
            },
            "duration": {
                "type": "integer",
                "enum": [4, 5, 6, 7, 8, 9, 10],
                "default": 5,
                "description": "Duration in seconds.",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                "default": "16:9",
                "description": "Mapped to the ARK 'ratio' field.",
            },
            "resolution": {
                "type": "string",
                "enum": ["480p", "720p", "1080p"],
                "default": "720p",
            },
            "generate_audio": {
                "type": "boolean",
                "default": True,
                "description": "Generate synchronized native audio",
            },
            "seed": {"type": "integer"},
            "image_url": {
                "type": "string",
                "description": "Start/first frame image URL for image_to_video",
            },
            "reference_image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Reference image URLs for reference_to_video",
            },
            "camera_fixed": {
                "type": "boolean",
                "default": False,
                "description": "Keep camera fixed (disable auto camera motion)",
            },
            "watermark": {
                "type": "boolean",
                "default": False,
                "description": "Add platform watermark to output",
            },
            "model": {
                "type": "string",
                "description": "Override SEEDANCE_MODEL (e.g. doubao-seedance-1-5-pro-251215)",
            },
            "ark_api_key": {"type": "string", "description": "Override ARK_API_KEY"},
            "ark_base_url": {"type": "string", "description": "Override ARK_BASE_URL"},
            "output_path": {"type": "string"},
            "poll_interval_seconds": {"type": "number", "default": 5.0},
            "timeout_seconds": {"type": "integer", "default": 600},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=500, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "operation", "duration", "seed"]

    # ------------------------------------------------------------------
    # Config resolution
    # ------------------------------------------------------------------

    def _api_key(self, inputs: dict[str, Any]) -> str | None:
        return inputs.get("ark_api_key") or os.environ.get("ARK_API_KEY")

    def _base_url(self, inputs: dict[str, Any]) -> str:
        return inputs.get("ark_base_url") or os.environ.get(
            "ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        ).rstrip("/")

    def _model(self, inputs: dict[str, Any]) -> str:
        return inputs.get("model") or os.environ.get(
            "SEEDANCE_MODEL", "doubao-seedance-1-5-pro-251215"
        )

    def get_status(self) -> ToolStatus:
        if self._api_key({}):
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    # ------------------------------------------------------------------
    # Cost / runtime estimation
    # ------------------------------------------------------------------

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        duration = inputs.get("duration", 5)
        secs = int(duration)
        # Per-second rate (USD). Override via SEEDANCE_COST_PER_SEC if your
        # account's rate differs (e.g. free trial -> 0).
        rate = float(os.environ.get("SEEDANCE_COST_PER_SEC", "0.14"))
        return round(rate * secs, 2)

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 180.0

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        import requests

        api_key = self._api_key(inputs)
        if not api_key:
            return ToolResult(
                success=False,
                error="ARK_API_KEY not set. " + self.install_instructions,
            )

        base_url = self._base_url(inputs)
        model = self._model(inputs)
        operation = inputs.get("operation", "text_to_video")
        start = time.time()

        # Build content blocks (ARK content_generation format)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": inputs["prompt"]}
        ]
        if operation == "image_to_video" and inputs.get("image_url"):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": inputs["image_url"]},
                    "role": "first_frame",
                }
            )
        for ref in inputs.get("reference_image_urls") or []:
            content.append(
                {"type": "image_url", "image_url": {"url": ref}, "role": "reference"}
            )

        body: dict[str, Any] = {
            "model": model,
            "content": content,
        }
        if inputs.get("duration") is not None:
            body["duration"] = int(inputs["duration"])
        if inputs.get("aspect_ratio"):
            body["ratio"] = inputs["aspect_ratio"]
        if inputs.get("resolution"):
            body["resolution"] = inputs["resolution"]
        if "generate_audio" in inputs:
            body["generate_audio"] = inputs["generate_audio"]
        if inputs.get("seed") is not None:
            body["seed"] = inputs["seed"]
        if inputs.get("camera_fixed") is not None:
            body["camera_fixed"] = inputs["camera_fixed"]
        if inputs.get("watermark") is not None:
            body["watermark"] = inputs["watermark"]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        submit_url = f"{base_url}/contents/generations/tasks"

        # --- Submit ---
        try:
            submit_resp = requests.post(
                submit_url, headers=headers, json=body, timeout=30
            )
            if submit_resp.status_code == 404:
                return ToolResult(
                    success=False,
                    error=(
                        f"Endpoint not found: {submit_url}\n"
                        "ARK content_generation path may differ for your region.\n"
                        f"Response: {submit_resp.text[:500]}"
                    ),
                )
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Seedance ARK submit failed: {e}",
            )

        task_id = (
            submit_data.get("id")
            or submit_data.get("task_id")
            or submit_data.get("request_id")
        )
        if not task_id:
            return ToolResult(
                success=False,
                error=f"Submit succeeded but no task id in response: {json.dumps(submit_data, ensure_ascii=False)[:500]}",
            )

        # --- Poll ---
        poll_interval = float(inputs.get("poll_interval_seconds", 5.0))
        timeout_seconds = int(inputs.get("timeout_seconds", 600))
        deadline = time.time() + timeout_seconds
        query_url = f"{base_url}/contents/generations/tasks/{task_id}"

        try:
            while time.time() < deadline:
                time.sleep(poll_interval)
                q_resp = requests.get(query_url, headers=headers, timeout=30)
                q_resp.raise_for_status()
                q_data = q_resp.json()
                status = str(q_data.get("status", "")).upper()
                if status in ("SUCCEEDED", "SUCCESS", "COMPLETED", "DONE"):
                    break
                if status in ("FAILED", "CANCELLED", "ERROR"):
                    err = q_data.get("error") or {}
                    return ToolResult(
                        success=False,
                        error=f"Seedance generation {status.lower()}: {err.get('message') or err or q_data.get('message', '')}",
                    )
                poll_interval = min(poll_interval * 1.1, 15.0)
            else:
                return ToolResult(
                    success=False,
                    error=f"Seedance poll timed out after {timeout_seconds}s for task {task_id}",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Seedance ARK poll failed: {e}",
            )

        # --- Extract video URL ---
        video_url = self._extract_video_url(q_data)
        if not video_url:
            return ToolResult(
                success=False,
                error=(
                    f"Task completed but no video URL found.\n"
                    f"Response keys: {list(q_data.keys())}\n"
                    f"Full response: {json.dumps(q_data, ensure_ascii=False)[:1000]}"
                ),
            )

        output_path = Path(inputs.get("output_path", "seedance_ark_output.mp4"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            video_response = requests.get(video_url, timeout=180)
            video_response.raise_for_status()
            output_path.write_bytes(video_response.content)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to download video from {video_url}: {e}",
            )

        from tools.video._shared import probe_output

        probed = probe_output(output_path)
        return ToolResult(
            success=True,
            data={
                "provider": "seedance",
                "gateway": "volcengine_ark",
                "model": model,
                "prompt": inputs["prompt"],
                "operation": operation,
                "aspect_ratio": inputs.get("aspect_ratio", "16:9"),
                "resolution": inputs.get("resolution", "720p"),
                "generate_audio": inputs.get("generate_audio", True),
                "seed": q_data.get("seed") or inputs.get("seed"),
                "revised_prompt": q_data.get("revised_prompt"),
                "task_id": task_id,
                "output": str(output_path),
                "output_path": str(output_path),
                "format": "mp4",
                **probed,
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )

    @staticmethod
    def _extract_video_url(q_data: dict[str, Any]) -> str | None:
        """Extract the generated video URL from the ARK response.

        Verified shape:
            { "content": { "video_url": "...", "last_frame_url": "...", "file_url": "..." } }
        Also try a few alternative shapes for robustness.
        """
        content = q_data.get("content")
        if isinstance(content, dict):
            for key in ("video_url", "file_url", "url"):
                if isinstance(content.get(key), str) and content[key]:
                    return content[key]
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if isinstance(item.get("video_url"), str) and item["video_url"]:
                        return item["video_url"]
                    if item.get("type") == "video_url" and isinstance(item.get("video_url"), str):
                        return item["video_url"]
        for key in ("video_url", "url", "file_url"):
            if isinstance(q_data.get(key), str) and q_data[key]:
                return q_data[key]
        out = q_data.get("output") or q_data.get("result") or {}
        if isinstance(out, dict):
            for key in ("video_url", "file_url", "url"):
                if isinstance(out.get(key), str) and out[key]:
                    return out[key]
        return None
