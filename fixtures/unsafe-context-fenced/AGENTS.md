# AGENTS.md

Fenced secret-like value should still be detected:

```text
api_key = "example-secret-value-1234567890"
token = example-unquoted-secret-value-1234567890
```

Fenced private key marker should still be detected:

```text
-----BEGIN FAKE PRIVATE KEY-----
not-real-key-material
-----END FAKE PRIVATE KEY-----
```

Fenced hidden Unicode should still be detected:

```text
zero​width
```

Harmless local cleanup example should not become an unsafe finding:

```bash
rm -rf ./build
rm -rf /tmp/lucid-example
```
