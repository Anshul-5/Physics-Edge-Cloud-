# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within PhysEdge-Cloud, please send an email to the maintainers. All security vulnerabilities will be promptly addressed.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix or mitigation**: Within 30 days for critical issues

## Security Considerations

### Firmware Security

- **Secure Boot**: Enable ESP32-S3 Secure Boot v2 for production deployments
- **Flash Encryption**: Enable flash encryption to protect firmware from extraction
- **JTAG Disable**: Disable JTAG interface in production to prevent debugging

### Network Security

- **TLS 1.3**: All cloud communications use TLS 1.3
- **Certificate Pinning**: Implement certificate pinning for gRPC connections
- **mTLS**: Support mutual TLS for device authentication

### Data Security

- **End-to-End Encryption**: Video data is encrypted at rest and in transit
- **No PII Storage**: Edge devices do not store personally identifiable information
- **Secure Erase**: Implement secure erase for sensitive data in PSRAM

### Physical Security

- **Tamper Detection**: Consider hardware tamper detection for sensitive deployments
- **Secure Storage**: Store cryptographic keys in ESP32-S3 secure element

## Best Practices

1. **Keep firmware updated** - Always use the latest stable release
2. **Use strong credentials** - Change default passwords and API keys
3. **Network segmentation** - Isolate IoT devices on separate VLANs
4. **Monitor logs** - Regularly review security logs for anomalies
5. **Backup configurations** - Maintain secure backups of device configurations

## Dependency Security

We regularly audit dependencies for known vulnerabilities:

- ESP-IDF: Updated to latest stable version
- Managed components: Reviewed quarterly
- CVE monitoring: Automated scanning in CI pipeline

## Contact

For security concerns, please contact the maintainers directly rather than opening a public issue.
