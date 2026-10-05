# Glossary targets

We use lwm2m over dtls in prose, which a linter should report.

Inline code such as `api` and `json` must not be reported.

```python
import json
resp = api.get("https://example.com/api/v1")
```

Visit https://example.com/api/v1 or read [the json guide](https://example.com/json.html).

<!-- a dtls comment that is not prose -->

The Pre-Shared Key (PSK) is defined here, and PSK is used afterwards.

This is wordy because in order to wrap lines, in order
to detect it we need to join them.
