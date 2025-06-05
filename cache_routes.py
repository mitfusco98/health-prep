
from flask import jsonify, render_template
from app import app
from cache_manager import cache_manager
from jwt_utils import admin_required

@app.route('/admin/cache/stats')
@admin_required
def cache_stats():
    """Get cache statistics"""
    stats = cache_manager.get_stats()
    return jsonify(stats)

@app.route('/admin/cache/clear', methods=['POST'])
@admin_required  
def clear_cache():
    """Clear all cache entries"""
    try:
        if cache_manager.redis_client:
            cache_manager.redis_client.flushdb()
        else:
            cache_manager.memory_cache.clear()
        
        return jsonify({'success': True, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/cache')
@admin_required
def cache_dashboard():
    """Cache management dashboard"""
    stats = cache_manager.get_stats()
    return render_template('cache_dashboard.html', stats=stats)
