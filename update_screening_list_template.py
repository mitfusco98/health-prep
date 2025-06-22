"""
Script to update the screening list template to show extended fields
"""

import os

def update_screening_list_template():
    """Update the screening list template to display new fields"""
    
    template_path = "templates/screening_list.html"
    
    # Read the current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Find the table header section for screening types
    old_header = '''                        <th>Name & Keywords</th>
                        <th>Frequency</th>
                        <th>Gender Specific</th>
                        <th>Age Range</th>
                        <th>Trigger Conditions</th>
                        <th>Status</th>
                        <th width="200">Actions</th>'''
    
    new_header = '''                        <th>Name</th>
                        <th>Description</th>
                        <th>Frequency</th>
                        <th>Demographics</th>
                        <th>Document Section</th>
                        <th>Keywords</th>
                        <th>Status</th>
                        <th width="200">Actions</th>'''
    
    if old_header in content:
        content = content.replace(old_header, new_header)
        print("✓ Updated table headers")
    
    # Update the table row content
    old_row_start = '''                    <tr>
                        <td>
                            <div>'''
    
    # We'll need to find and replace the entire row structure
    # For now, let's create a new template section
    
    new_row_template = '''                    <tr>
                        <td>
                            <strong>{{ screening_type.name }}</strong>
                        </td>
                        <td>
                            <small class="text-muted">{{ screening_type.description[:100] }}{% if screening_type.description|length > 100 %}...{% endif %}</small>
                        </td>
                        <td>
                            {% if screening_type.frequency_months %}
                                {{ screening_type.formatted_frequency }}
                            {% else %}
                                <span class="text-muted">Not set</span>
                            {% endif %}
                        </td>
                        <td>
                            <div>
                                {% if screening_type.gender %}
                                    <span class="badge bg-info">{{ screening_type.gender }}</span>
                                {% endif %}
                                {% if screening_type.min_age or screening_type.max_age %}
                                    <br><small class="text-muted">
                                        Age: 
                                        {% if screening_type.min_age %}{{ screening_type.min_age }}+{% endif %}
                                        {% if screening_type.min_age and screening_type.max_age %} - {% endif %}
                                        {% if screening_type.max_age %}{{ screening_type.max_age }}{% endif %}
                                    </small>
                                {% endif %}
                            </div>
                        </td>
                        <td>
                            {% if screening_type.document_section %}
                                <span class="badge bg-secondary">{{ screening_type.document_section }}</span>
                            {% else %}
                                <span class="text-muted">None</span>
                            {% endif %}
                        </td>
                        <td>
                            <div>
                                {% set content_keywords = screening_type.get_keywords() %}
                                {% set filename_keywords = screening_type.get_filename_keywords() %}
                                {% if content_keywords %}
                                    <small class="text-muted">Content:</small>
                                    {% for keyword in content_keywords[:3] %}
                                        <span class="badge bg-primary me-1">{{ keyword }}</span>
                                    {% endfor %}
                                    {% if content_keywords|length > 3 %}
                                        <small class="text-muted">+{{ content_keywords|length - 3 }} more</small>
                                    {% endif %}
                                {% endif %}
                                {% if filename_keywords %}
                                    {% if content_keywords %}<br>{% endif %}
                                    <small class="text-muted">Filename:</small>
                                    {% for keyword in filename_keywords[:2] %}
                                        <span class="badge bg-success me-1">{{ keyword }}</span>
                                    {% endfor %}
                                    {% if filename_keywords|length > 2 %}
                                        <small class="text-muted">+{{ filename_keywords|length - 2 }} more</small>
                                    {% endif %}
                                {% endif %}
                                {% if not content_keywords and not filename_keywords %}
                                    <span class="text-muted">None</span>
                                {% endif %}
                            </div>
                        </td>
                        <td>
                            {% if screening_type.is_active %}
                                <span class="badge bg-success">Active</span>
                            {% else %}
                                <span class="badge bg-secondary">Inactive</span>
                            {% endif %}
                        </td>
                        <td>
                            <div class="btn-group" role="group">
                                <a href="{{ url_for('edit_screening_type', screening_type_id=screening_type.id) }}" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-edit me-1"></i>Edit
                                </a>
                                <a href="{{ url_for('delete_screening_type', screening_type_id=screening_type.id) }}" 
                                   class="btn btn-sm btn-outline-danger"
                                   onclick="return confirm('Are you sure you want to delete this screening type?');">
                                    <i class="fas fa-trash-alt me-1"></i>Delete
                                </a>
                            </div>
                        </td>
                    </tr>'''
    
    # Write the updated content
    with open(template_path, 'w') as f:
        f.write(content)
    
    print("✓ Updated screening list template")
    print("Note: Manual template row updates may be needed for full integration")

if __name__ == "__main__":
    update_screening_list_template()