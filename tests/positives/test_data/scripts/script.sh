#!/bin/bash
pip install --extra-index-url https://pypi.org/simple unclaimed-package-s2==1.0.0


npm install unclaimed-package-t2


cd /tmp ; pip install unclaimed-package-u2==1.0.0 ; apt-get install something ; other-command --useless-flag arguments ; \ 
    && echo "Hello, world!" ; pwd ; awk '{print $1}' ; \
    npm update ; npm audit fix ; \
    npm install unclaimed-package-v2@1.0.0 ; \
    npm install unclaimed-package-w2@1.0.0 --save-dev ; \
    npm install unclaimed-package-x2@1.0.0 --save-exact ; \
    npm install unclaimed-package-x2@1.0.0 --save-dev --save-exact ; \
    npm install unclaimed-package-y2@1.0.0 --save-dev --save-exact ; \
    npm install @testorg/unclaimed-package-z2@1.0.0 ; # false positive

exit 0

# should find:
# pip: unclaimed-package-s2 unclaimed-package-u2
# npm: unclaimed-package-t2 unclaimed-package-v2 unclaimed-package-w2 unclaimed-package-x2 (x2) unclaimed-package-y2 @testorg/unclaimed-package-z2