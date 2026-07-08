import os, json
# Use the real config supplied by the user
os.environ['ARK_API_KEY'] = 'ark-4d743f40-cb51-4164-a679-2a85e1675d74-6c585'
os.environ['ARK_BASE_URL'] = 'https://ark.cn-beijing.volces.com/api/v3'
os.environ['SEEDANCE_MODEL'] = 'doubao-seedance-1-5-pro-251215'

from tools.tool_registry import registry
registry.discover()
t = registry.get('seedance_ark')

res = t.execute({
    'prompt': 'A calm ocean wave gently rolling onto a sandy beach at golden hour, slow cinematic camera.',
    'operation': 'text_to_video',
    'duration': 4,
    'aspect_ratio': '16:9',
    'resolution': '720p',
    'output_path': 'ark_live_test.mp4',
    'poll_interval_seconds': 5,
    'timeout_seconds': 600,
})
print(json.dumps({
    'success': res.success,
    'error': res.error,
    'output': res.data.get('output') if res.data else None,
    'cost_usd': res.cost_usd,
    'duration_seconds': res.duration_seconds,
    'model': res.model,
}, ensure_ascii=False, indent=2))
