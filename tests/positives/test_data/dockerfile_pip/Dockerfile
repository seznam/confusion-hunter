FROM python:3.9
# ruleid: generated-rule-dockerfile
RUN pip install --extra-index-url https://pypi.org/simple unclaimed-package-h==1.0.0


# ruleid: generated-rule-dockerfile
RUN pip install unclaimed-package-i --extra-index-url https://pypi.org/

# ok: generated-rule-dockerfile
RUN pip install unclaimed-package-l --index-url https://pypi.internal.org/

# ruleid: dockerfile-extra-index
RUN pip install --extra-index-url https://pypi.org/simple unclaimed-package-q2    

# ruleid: dockerfile-missing-internal
RUN pip install unclaimed-package-m




# ruleid: dockerfile-extra-index
RUN pip install --extra-index-url https://pypi.org/simple unclaimed-package-r2

# ruleid: dockerfile-missing-internal
RUN pip install unclaimed-package-n

# ruleid: dockerfile-env-default-not-set
ENV UV_DEFAULT_INDEX=https://pypi.org/simple
RUN uv pip install unclaimed-package-o

# ok: dockerfile-correct-internal
ENV UV_DEFAULT_INDEX=https://pypi.repo.ops.example.com/simple
RUN uv pip install unclaimed-package-p

RUN pip install unclaimed-package-j \
                another-library \
                testing-library




