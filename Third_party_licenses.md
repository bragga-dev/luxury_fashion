# Licenças de terceiros

Gerado com `pip-licenses` a partir de requirements.txt. Regenerar a cada atualização de dependências:

`pip-licenses --format=markdown --order=license > THIRD_PARTY_LICENSES.md`

Pontos de atenção (copyleft fraco, uso sem modificação, sem problema para software fechado): **psycopg / psycopg2-binary** (LGPL), **certifi** (MPL-2.0), **pyphen** (GPL/LGPL/MPL — dependência do WeasyPrint).

Imagens de contêiner: PostgreSQL (licença PostgreSQL), Redis 7 (7.4+ sob RSALv2/SSPL — uso interno como cache/broker), MinIO (AGPLv3, usado sem modificações).

| Name                          | Version     | License                                                                                                                                        |
|-------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| multidict                     | 6.7.1       | Apache License 2.0                                                                                                                             |
| aiosignal                     | 1.4.0       | Apache Software License                                                                                                                        |
| django-ratelimit              | 4.1.0       | Apache Software License                                                                                                                        |
| google-auth                   | 2.35.0      | Apache Software License                                                                                                                        |
| propcache                     | 0.5.2       | Apache Software License                                                                                                                        |
| requests                      | 2.34.1      | Apache Software License                                                                                                                        |
| rsa                           | 4.9.1       | Apache Software License                                                                                                                        |
| s3transfer                    | 0.17.0      | Apache Software License                                                                                                                        |
| zopfli                        | 0.4.1       | Apache Software License                                                                                                                        |
| python-dateutil               | 2.9.0.post0 | Apache Software License; BSD License                                                                                                           |
| contextlib2                   | 21.6.0      | Apache Software License; Python Software Foundation License                                                                                    |
| boto3                         | 1.43.6      | Apache-2.0                                                                                                                                     |
| botocore                      | 1.43.6      | Apache-2.0                                                                                                                                     |
| coverage                      | 7.14.1      | Apache-2.0                                                                                                                                     |
| frozenlist                    | 1.8.0       | Apache-2.0                                                                                                                                     |
| phonenumbers                  | 9.0.30      | Apache-2.0                                                                                                                                     |
| tzdata                        | 2026.2      | Apache-2.0                                                                                                                                     |
| yarl                          | 1.23.0      | Apache-2.0                                                                                                                                     |
| aiohttp                       | 3.13.5      | Apache-2.0 AND MIT                                                                                                                             |
| packaging                     | 26.2        | Apache-2.0 OR BSD-2-Clause                                                                                                                     |
| cryptography                  | 48.0.0      | Apache-2.0 OR BSD-3-Clause                                                                                                                     |
| injector                      | 0.24.0      | BSD                                                                                                                                            |
| amqp                          | 5.3.1       | BSD License                                                                                                                                    |
| asgiref                       | 3.11.1      | BSD License                                                                                                                                    |
| billiard                      | 4.2.4       | BSD License                                                                                                                                    |
| click-plugins                 | 1.1.1.2     | BSD License                                                                                                                                    |
| cssselect2                    | 0.9.0       | BSD License                                                                                                                                    |
| django-ninja-simple-jwt       | 0.8.1       | BSD License                                                                                                                                    |
| django-storages               | 1.14.6      | BSD License                                                                                                                                    |
| prompt_toolkit                | 3.0.52      | BSD License                                                                                                                                    |
| pyasn1_modules                | 0.4.2       | BSD License                                                                                                                                    |
| pydyf                         | 0.12.1      | BSD License                                                                                                                                    |
| pytest-django                 | 4.12.0      | BSD License                                                                                                                                    |
| sqlparse                      | 0.5.5       | BSD License                                                                                                                                    |
| tinycss2                      | 1.5.1       | BSD License                                                                                                                                    |
| vine                          | 5.1.0       | BSD License                                                                                                                                    |
| weasyprint                    | 68.1        | BSD License                                                                                                                                    |
| webencodings                  | 0.5.1       | BSD License                                                                                                                                    |
| Pygments                      | 2.20.0      | BSD-2-Clause                                                                                                                                   |
| pyasn1                        | 0.6.4       | BSD-2-Clause                                                                                                                                   |
| Django                        | 6.0.5       | BSD-3-Clause                                                                                                                                   |
| celery                        | 5.6.3       | BSD-3-Clause                                                                                                                                   |
| click                         | 8.3.3       | BSD-3-Clause                                                                                                                                   |
| idna                          | 3.15        | BSD-3-Clause                                                                                                                                   |
| kombu                         | 5.6.2       | BSD-3-Clause                                                                                                                                   |
| pycparser                     | 3.0         | BSD-3-Clause                                                                                                                                   |
| python-dotenv                 | 1.2.2       | BSD-3-Clause                                                                                                                                   |
| uvicorn                       | 0.46.0      | BSD-3-Clause                                                                                                                                   |
| pyphen                        | 0.17.2      | GNU General Public License v2 or later (GPLv2+); GNU Lesser General Public License v2 or later (LGPLv2+); Mozilla Public License 1.1 (MPL 1.1) |
| psycopg2-binary               | 2.9.12      | GNU Library or Lesser General Public License (LGPL)                                                                                            |
| dnspython                     | 2.8.0       | ISC License (ISCL)                                                                                                                             |
| psycopg                       | 3.3.4       | LGPL-3.0-only                                                                                                                                  |
| psycopg-binary                | 3.3.4       | LGPL-3.0-only                                                                                                                                  |
| PyJWT                         | 2.12.1      | MIT                                                                                                                                            |
| attrs                         | 26.1.0      | MIT                                                                                                                                            |
| brotli                        | 1.2.0       | MIT                                                                                                                                            |
| cffi                          | 2.0.0       | MIT                                                                                                                                            |
| charset-normalizer            | 3.4.7       | MIT                                                                                                                                            |
| click-repl                    | 0.3.0       | MIT                                                                                                                                            |
| django-cors-headers           | 4.9.0       | MIT                                                                                                                                            |
| django-environ                | 0.13.0      | MIT                                                                                                                                            |
| django-extensions             | 4.1         | MIT                                                                                                                                            |
| fonttools                     | 4.62.1      | MIT                                                                                                                                            |
| gunicorn                      | 26.0.0      | MIT                                                                                                                                            |
| iniconfig                     | 2.3.0       | MIT                                                                                                                                            |
| pydantic                      | 2.13.4      | MIT                                                                                                                                            |
| pydantic-settings             | 2.14.1      | MIT                                                                                                                                            |
| pydantic_core                 | 2.46.4      | MIT                                                                                                                                            |
| pytest                        | 9.1.0       | MIT                                                                                                                                            |
| pytest-cov                    | 7.1.0       | MIT                                                                                                                                            |
| redis                         | 7.4.0       | MIT                                                                                                                                            |
| typing-inspection             | 0.4.2       | MIT                                                                                                                                            |
| urllib3                       | 2.7.0       | MIT                                                                                                                                            |
| validate-docbr                | 2.0.0       | MIT                                                                                                                                            |
| whitenoise                    | 6.12.0      | MIT                                                                                                                                            |
| annotated-types               | 0.7.0       | MIT License                                                                                                                                    |
| brazilcep                     | 7.0.1       | MIT License                                                                                                                                    |
| cachetools                    | 5.5.2       | MIT License                                                                                                                                    |
| click-didyoumean              | 0.3.1       | MIT License                                                                                                                                    |
| colorlog                      | 6.10.1      | MIT License                                                                                                                                    |
| django-cleanup                | 9.0.0       | MIT License                                                                                                                                    |
| django-encrypted-model-fields | 0.6.5       | MIT License                                                                                                                                    |
| django-ninja                  | 1.6.2       | MIT License                                                                                                                                    |
| django-ninja-extra            | 0.31.4      | MIT License                                                                                                                                    |
| django-ninja-jwt              | 5.4.4       | MIT License                                                                                                                                    |
| django-phonenumber-field      | 8.4.0       | MIT License                                                                                                                                    |
| h11                           | 0.16.0      | MIT License                                                                                                                                    |
| jmespath                      | 1.1.0       | MIT License                                                                                                                                    |
| pluggy                        | 1.6.0       | MIT License                                                                                                                                    |
| six                           | 1.17.0      | MIT License                                                                                                                                    |
| tinyhtml5                     | 2.1.0       | MIT License                                                                                                                                    |
| tzlocal                       | 5.3.1       | MIT License                                                                                                                                    |
| pillow                        | 12.2.0      | MIT-CMU                                                                                                                                        |
| certifi                       | 2026.4.22   | Mozilla Public License 2.0 (MPL 2.0)                                                                                                           |
| typing_extensions             | 4.15.0      | PSF-2.0                                                                                                                                        |
| aiohappyeyeballs              | 2.6.1       | Python Software Foundation License                                                                                                             |
| email-validator               | 2.3.0       | The Unlicense (Unlicense)                                                                                                                      |