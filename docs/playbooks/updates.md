# Progress Updates

If the `progress_url` was set in the API request, LSO will send periodical playbook execution updates to this endpoint.
These updates take the following shape.

```JSON
{
  "progress": [
    {"title": "We're getting there!"}
  ]
}
```

Updates are send whenever the Ansible runner has an update. In practice this will be when a step has completed while
running the playbook.
