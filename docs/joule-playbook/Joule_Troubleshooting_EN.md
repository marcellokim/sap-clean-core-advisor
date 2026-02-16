# Joule Troubleshooting (EN)

## Common Issues
1. Authentication failure
- Check: API key, authorization, role mapping
- Action: re-grant role, rotate key

2. Response latency
- Check: retry policy, network, quota
- Action: tune timeout/retry, force fallback

3. Missing evidence trace
- Check: rule_reference_map and source catalog
- Action: add missing rule-to-source links
