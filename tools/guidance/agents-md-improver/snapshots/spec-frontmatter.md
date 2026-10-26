### Frontmatter

| Field | Required | Constraints |
| - | - | - |
| `name` | Yes | Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen. |
| `description` | Yes | Max 1024 characters. Non-empty. Describes what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled license file. |
| `compatibility` | No | Max 500 characters. Indicates environment requirements (intended product, system packages, network access, etc.). |
| `metadata` | No | Arbitrary key-value mapping for additional metadata (a map from string keys to string values). |
| `allowed-tools` | No | Space-separated string of pre-approved tools the skill may use. (Experimental) |

> **Minimal example:**
>
> ```markdown SKILL.md theme={null}
> ---
> name: skill-name
> description: A description of what this skill does and when to use it.
> ---
> ```
>
> **Example with optional fields:**
>
> ```markdown SKILL.md theme={null}
> ---
> name: pdf-processing
> description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
> license: Apache-2.0
> metadata:
>   author: example-org
>   version: "1.0"
> ---
> ```

#### `name` field

The required `name` field:

* Must be 1-64 characters
* May only contain unicode lowercase alphanumeric characters (`a-z`, `0-9`) and hyphens (`-`)
* Must not start or end with a hyphen (`-`)
* Must not contain consecutive hyphens (`--`)
* Must match the parent directory name

> **Valid examples:**
>
> ```yaml theme={null}
> name: pdf-processing
> ```
>
> ```yaml theme={null}
> name: data-analysis
> ```
>
> ```yaml theme={null}
> name: code-review
> ```
>
> **Invalid examples:**
>
> ```yaml theme={null}
> name: PDF-Processing  # uppercase not allowed
> ```
>
> ```yaml theme={null}
> name: -pdf  # cannot start with hyphen
> ```
>
> ```yaml theme={null}
> name: pdf--processing  # consecutive hyphens not allowed
> ```

#### `description` field

The required `description` field:

* Must be 1-1024 characters
* Should describe both what the skill does and when to use it
* Should include specific keywords that help agents identify relevant tasks

> **Good example:**
>
> ```yaml theme={null}
> description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
> ```
>
> **Poor example:**
>
> ```yaml theme={null}
> description: Helps with PDFs.
> ```

#### `license` field

The optional `license` field:

* Specifies the license applied to the skill
* We recommend keeping it short (either the name of a license or the name of a bundled license file)

> **Example:**
>
> ```yaml theme={null}
> license: Proprietary. LICENSE.txt has complete terms
> ```

#### `compatibility` field

The optional `compatibility` field:

* Must be 1-500 characters if provided
* Should only be included if your skill has specific environment requirements
* Can indicate intended product, required system packages, network access needs, etc.

> **Examples:**
>
> ```yaml theme={null}
> compatibility: Designed for Claude Code (or similar products)
> ```
>
> ```yaml theme={null}
> compatibility: Requires git, docker, jq, and access to the internet
> ```
>
> ```yaml theme={null}
> compatibility: Requires Python 3.14+ and uv
> ```

> [!NOTE]
>
> Most skills do not need the `compatibility` field.

#### `metadata` field

The optional `metadata` field:

* A map from string keys to string values
* Clients can use this to store additional properties not defined by the Agent Skills spec
* We recommend making your key names reasonably unique to avoid accidental conflicts

> **Example:**
>
> ```yaml theme={null}
> metadata:
>   author: example-org
>   version: "1.0"
> ```

#### `allowed-tools` field

The optional `allowed-tools` field:

* A space-separated string of tools that are pre-approved to run
* Experimental. Support for this field may vary between agent implementations

> **Example:**
>
> ```yaml theme={null}
> allowed-tools: Bash(git:*) Bash(jq:*) Read
> ```
