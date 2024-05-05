# Django Activity Log: Track User Actions and Requests

## Introduction

The Django Activity Log package provides a comprehensive solution for logging various activities within your Django application, including user actions, request events, model changes (CRUD operations), and authentication events. This logging capability is essential for security audits, compliance requirements, debugging, and gaining insights into user behavior.

## Installation

1. Install the package via pip:

```bash
pip install django_activitylog_jwt
```

2. Add 'activitylog' to your INSTALLED_APPS list in settings.py:
```bash
INSTALLED_APPS = [
    # ... other apps
    'activitylog',
]
```

3. Add 'activitylog.middleware.middleware.ActivityLogMiddleware' to your MIDDLEWARE list in settings.py:
```bash
MIDDLEWARE = [
    # ... other middleware
    'activitylog.middleware.middleware.ActivityLogMiddleware',
] 
```
4. (Optional) If you are using CORS (Cross-Origin Resource Sharing), add 'x-frontend-url' to your CORS_ALLOW_HEADERS list in settings.py to capture the frontend URL in request events:
```bash
CORS_ALLOW_HEADERS = [
    'x-frontend-url',
    # ... other headers
]
```

### Frontend Integration (Optional but Recommended)
To capture the frontend URL for request event logging, include the following JavaScript code in your frontend:
```bash 
const frontendUrl = window.location.href;

fetch('your-api-endpoint', {
  method: 'GET', // or 'POST', 'PUT', etc.
  headers: {
    'X-Frontend-URL': frontendUrl,
    'Content-Type': 'application/json' // Example of another header
    // Add more headers as needed
  },
  // Add body for POST or PUT requests if required
})
  .then(response => {
    // Handle response
  })
  .catch(error => {
    // Handle errors
  });

```

## Configuration (Optional)
### Customize the behavior of the Activity Log using settings in settings.py:

settings.py
 ```bash
DJANGO_ACTIVITY_LOG_WATCH_AUTH_EVENTS = True
DJANGO_ACTIVITY_LOG_WATCH_MODEL_EVENTS = True
DJANGO_ACTIVITY_LOG_WATCH_REQUEST_EVENTS = True
DJANGO_ACTIVITY_LOG_WATCH_CORS_EVENTS = True
DJANGO_ACTIVITY_LOG_REMOTE_ADDR_HEADER = 'REMOTE_ADDR'  # Default header containing client's IP address
DJANGO_ACTIVITY_LOG_BROWSER = 'User-Agent'  # Optional: Customize the header containing browser information
DJANGO_ACTIVITY_LOG_PLATFORM = 'Platform'  # Optional: Customize the header containing platform information
DJANGO_ACTIVITY_LOG_OPERATING_SYSTEM = 'OS'  # Optional: Customize the header containing operating system information
DJANGO_ACTIVITY_LOG_USER_DB_CONSTRAINT = True  # Optional: Control user deletion behavior (default: True to prevent deletion)
DJANGO_ACTIVITY_LOG_LOGGING_BACKEND = 'activitylog.backends.ModelBackend'  # Set the logging backend (default: activitylog.backends.ModelBackend)
DJANGO_ACTIVITY_LOG_UNREGISTERED_CLASSES_DEFAULT = []  # Define models to exclude from logging (default: empty)
DJANGO_ACTIVITY_LOG_REGISTERED_CLASSES = []  # Define models to include explicitly (overrides default behavior)
DJANGO_ACTIVITY_LOG_UNREGISTERED_URLS_DEFAULT = ['/admin/', '/static/']  # Define URLs to exclude from logging
DJANGO_ACTIVITY_LOG_REGISTERED_URLS = []  # Define URLs to include explicitly (overrides default behavior)
DJANGO_ACTIVITY_LOG_ADMIN_SHOW_MODEL_EVENTS = True  # Show model events in Django Admin (default: True)
DJANGO_ACTIVITY_LOG_ADMIN_SHOW_AUTH_EVENTS = True  # Show authentication events in Django Admin (default: True)
DJANGO_ACTIVITY_LOG_ADMIN_SHOW_REQUEST_EVENTS = True  # Show request events in Django Admin (default: True)
DJANGO_ACTIVITY_LOG_ADMIN_SHOW_CORS_EVENTS = True  # Show CORS events in Django Admin (default: True)
```
