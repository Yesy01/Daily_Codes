# Python Script Design Learning Curve

This is the thinking process I used while building `verify_posters.py`.

## Start With The Job

Before writing code, reduce the task to one sentence:

`verify_posters.py` should run an SVG generator for several seeds, hash the outputs, extract traits, write a JSON report, and fail if determinism breaks.

That one sentence gives the script its structure.

## Think In Inputs, Process, Outputs

I find it useful to split a script into:

- inputs
- process
- outputs
- failures

For this project:

- inputs: generator path, seeds file, output directory, run count, report path
- process: run generator, read SVG, hash file, extract traits, build results
- outputs: SVG files and one JSON report
- failures: missing files, generator crash, non-deterministic output

Once that is clear, the code usually becomes easier to plan.

## How I Pick Imports

I do not start by importing random libraries. I ask what operations the script needs.

- command-line flags: `argparse`
- JSON output: `json`
- hashing file bytes: `hashlib`
- path handling: `pathlib.Path`
- regex text extraction: `re`
- subprocess execution: `subprocess`
- current Python interpreter: `sys`
- executable checks: `os`

Imports should come from required capabilities, not habit.

## When I Use Functions

I use functions when the program is mostly a sequence of steps.

Each function should have one clear job:

- `parse_args()` reads CLI input
- `read_seeds()` loads seeds from disk
- `build_gen_cmd()` decides how to call the generator
- `run_generator()` executes one generator run
- `sha256_file()` hashes an output file
- `extract_traits()` pulls useful values from SVG text
- `main()` coordinates the workflow

This style works well when data flows from one step to the next.

## When I Use A Class

I reach for a class when state and behavior belong together.

Examples:

- a `PosterVerifier` object that stores generator path, output directory, and run count
- a `SeedResult` object for one seed's hashes, traits, and determinism result

For `verify_posters.py`, a class is not necessary because the script is a straightforward pipeline. Functions are simpler and easier to read.

## How I Decide Function Order

There are two useful orders:

### 1. Planning order

I usually think top-down:

- what should `main()` do?
- what helper steps does `main()` need?

That often looks like this:

```python
def main():
    # parse args
    # validate paths
    # read seeds
    # run generator for each seed
    # hash outputs
    # extract traits
    # write report
    # return success or failure
```

### 2. File order

For readability, I usually place code in this order:

- imports
- constants
- helper functions
- main workflow
- entrypoint

That helps the file read like a clean story.

## What Good Code Usually Looks Like

Good code is usually not the smartest-looking code. It is:

- correct
- readable
- easy to test
- easy to change
- clear about failure conditions

For scripts, I try to keep these rules:

- one function, one job
- validate early
- name things clearly
- keep side effects obvious
- write outputs in a stable format
- return useful exit codes

## A Practical Writing Workflow

When I start a new Python script, I use this sequence:

1. Write the goal in one sentence.
2. List the inputs and outputs.
3. Write rough pseudocode for `main()`.
4. Turn repeated or well-named steps into helper functions.
5. Add only the imports needed for those helpers.
6. Make the script run once.
7. Clean up names, comments, and error messages.

## Key Lesson From Day Two

The best structure depends on the problem shape.

`verify_posters.py` is not modeling a complex domain. It is running a workflow. That is why a function-based design is the right choice here.

If the project later grows to include reusable verifier objects, multiple report formats, or many verification strategies, that would be a better time to introduce classes.
