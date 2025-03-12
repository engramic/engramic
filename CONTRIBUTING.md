# Contributing to the Project  

Thank you for your interest in contributing! We appreciate your efforts in making this project better. We’re excited to have you in the community and look forward to your contributions!

### Contribution Workflow 

Our contribution workflow is evolving, and we will update this document soon with more details. Stay tuned!  

### Contributor License Agreement (CLA)  

Before your first pull request can be merged, you will need to sign and complete our Contributor License Agreement (CLA). You can preview it here:  
[https://www.engramic.org/cla](https://www.engramic.org/cla)  


## Pre-Commit Checklist

Before committing your changes, ensure the following steps are completed:

**Code Formatting & Style**

Ensure code is formatted correctly using Hatch:

```
hatch shell
hatch fmt
```


#### Testing & Validation
Execute the test suite to ensure all tests pass:

```
hatch shell 
hatch test -a
```

Check static typing:

Run type checking using Hatch:

```
hatch shell test
hatch run typecheck
```

#### Documentation & Environment
Add documentation to new code.

```
hatch shell docs
hatch run build
hatch run serve
```

#### Commit Message Guidelines

Follow a consistent commit message format to improve readability and tracking.

#### Commit Prefixes

| Prefix | Description                         |
|--------|-------------------------------------|
| **ENH:** | Enhancement, new functionality      |
| **BUG:** | Bug fix                             |
| **DOC:** | Additions/updates to documentation  |
| **TST:** | Additions/updates to tests          |
| **BLD:** | Updates to the build process/scripts|
| **PERF:**| Performance improvement             |
| **TYP:** | Type annotations                    |
| **CLN:** | Code cleanup                        |

#### Example Commit Message

```
git commit -m "ENH: Add support for additional config options"
```
