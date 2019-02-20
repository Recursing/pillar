from pillar.api.node_types import attachments_embedded_schema
from pillar.api.node_types.utils import markdown_fields

node_type_comment = {
    'name': 'comment',
    'description': 'Comments for asset nodes, pages, etc.',
    'dyn_schema': {
        # The actual comment content
        **markdown_fields(
            'content',
            minlength=5,
            required=True),
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'flagged',
                'edited'
            ],
        },
        # Total count of positive ratings (updated at every rating action)
        'rating_positive': {
            'type': 'integer',
        },
        # Total count of negative ratings (updated at every rating action)
        'rating_negative': {
            'type': 'integer',
        },
        # Collection of ratings, keyed by user
        'ratings': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'user': {
                        'type': 'objectid'
                    },
                    'is_positive': {
                        'type': 'boolean'
                    },
                    # Weight of the rating based on user rep and the context.
                    # Currently we have the following weights:
                    # - 1 auto null
                    # - 2 manual null
                    # - 3 auto valid
                    # - 4 manual valid
                    'weight': {
                        'type': 'integer'
                    }
                }
            }
        },
        'confidence': {'type': 'float'},
        'is_reply': {'type': 'boolean'},
        'attachments': attachments_embedded_schema,
    },
    'form_schema': {},
    'parent': ['asset', 'comment'],
}
