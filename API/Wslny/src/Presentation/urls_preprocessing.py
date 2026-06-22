def prepend_v1_prefix(endpoints, **kwargs):
    return [
        (
            path.replace("api/", "api/v1/", 1) if path.startswith("api/") else path,
            path_prefix,
            schema,
            url,
        )
        for path, path_prefix, schema, url in endpoints
    ]
