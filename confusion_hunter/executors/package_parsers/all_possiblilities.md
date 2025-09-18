# Registry packages
npm install lodash
npm install express@4.17.1
npm install @nestjs/core
npm install @types/node@18.0.0
npm install is-even@^1.0.0
npm install chalk@"16 - 17"
npm install sax@">=0.1.0 <0.2.0"
npm install ansi-regex --save-bundle
npm install readable-stream --save-exact
npm install node-tap --save-dev
npm install dtrace-provider --save-optional

# Aliased packages
npm install react16@npm:react@16
npm install react17@npm:react@17
npm install my-react@npm:react
npm install legacyj@npm:jquery@1
npm install npa@npm:npm-package-arg

# Multiline installs
npm install \
  lodash \
  express \
  moment@2.29.1 \
  @types/express

# Quoted versions
npm install "sax@>=0.1.0 <0.2.0"
npm install '@types/jest@^27.0.0'

# Git URLs
npm install git+https://github.com/mondora/asteroid.git
npm install git+https://github.com/user/repo.git#v1.0.0
npm install git+https://github.com/user/repo.git#semver:^2.0.0
npm install git+ssh://git@github.com:npm/npm.git#v1.0.27
npm install git://github.com/npm/cli.git#v1.0.27
npm install git+file:///home/user/code/my-package.git

# GitHub shorthands
npm install user/project
npm install github:user/project
npm install github:user/project#v1.2.3
npm install github:user/project#semver:^2.1.0

# GitLab shorthands
npm install gitlab:user/project
npm install gitlab:user/project#semver:^3.0

# Bitbucket shorthands
npm install bitbucket:user/repo
npm install bitbucket:user/repo#commitish

# Gist installs
npm install gist:101a11beef
npm install gist:user/101a11beef

# Local folders
npm install ./local-package
npm install ../relative-package
npm install /absolute/path/to/package

# Tarballs (local)
npm install ./packages/my-lib.tgz
npm install ../my-package.tar.gz
npm install /home/user/package.tgz

# Tarballs (remote)
npm install https://example.com/packages/pkg.tgz
npm install https://registry.example.com/my-package-v1.0.0.tgz
npm install https://github.com/indexzero/forever/tarball/v0.5.6

# With flags (should be ignored by parser)
npm install lodash --save
npm install lodash --save-dev
npm install lodash --save-optional
npm install lodash --save-exact
npm install lodash --global
npm install lodash --no-save
npm install lodash --dry-run
npm install lodash --force
npm install lodash --package-lock-only

# Broken or ambiguous cases (for robustness testing)
npm install github:user
npm install foo@bar@baz
npm install
npm install --global
npm install ./nonexistent
npm install "@scope/malformed"
npm install "invalid@semver@1.2.3"
npm install my-pkg@npm:  # missing real package
npm install git+https://github.com/user/  # incomplete repo
npm install git+file://  # invalid local git

# Combo installs
npm install react@17.0.2 express git+https://github.com/user/repo.git ./localpkg ../anotherpkg.tgz
