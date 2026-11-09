# tba-codec-x509-logotype

DER decoder for the subject logotype in X.509 certificates.

`decode_subject_logotype` takes the DER extension value and returns the
subject's direct image metadata or indirect reference. It exposes media types,
digests, and URIs for the consumer to evaluate. It performs no retrieval,
rendering, or BIMI-specific validation.

```python
from tba_codec_x509_logotype import decode_subject_logotype

subject = decode_subject_logotype(extension_der)
if subject is not None:
    for image in subject.images:
        print(image.media_type, image.uris)
```
