# Tests

Organized test cases for manual + automated verification of the YAPar generator.

## Layout

```
tests/
  cases/                       Self-contained test cases (one folder each)
    01_arithmetic_id/          Lexer + grammar + input + expected
    02_arithmetic_extended/
    03_arithmetic_numbers/
    04_assignments/
    05_classes_functions/
    06_rejection_examples/     Negative tests (should REJECT)
  legacy/                      Old layout (kept for reference)
    first_test/                Original .yal + input files
    Second_test/               Sample Python programs
    inputs/                    Misc .yal experiments
    grammars/                  Old grammar folder (now under cases/)
```

## Per-case contract

Every folder under `cases/` contains exactly:
- `lexer.yal`     — YALex specification (tokens)
- `grammar.yapar` — YAPar specification (productions)
- `input.txt`     — One input string per line
- `README.md`     — Description, expected outcome, run command

## Running a case from the CLI

```bash
python src/main.py --cli tests/cases/<CASE>/lexer.yal tests/cases/<CASE>/grammar.yapar tests/cases/<CASE>/input.txt
```

Example:
```bash
python src/main.py --cli tests/cases/05_classes_functions/lexer.yal tests/cases/05_classes_functions/grammar.yapar tests/cases/05_classes_functions/input.txt
```

## Running a case from the GUI

```bash
python src/main.py
```

Then:
1. **Open YALex** → pick `tests/cases/<CASE>/lexer.yal`
2. **Open YAPar** → pick `tests/cases/<CASE>/grammar.yapar`
3. **Open Input** → pick `tests/cases/<CASE>/input.txt`
4. Press **Analyze (Ctrl+R)**
5. Inspect tabs: Editor (highlight per line), LR(0), Tables, Parse Tree, Steps, Results

## Run all cases at once

PowerShell:
```powershell
$cases = @("01_arithmetic_id","02_arithmetic_extended","03_arithmetic_numbers","04_assignments","05_classes_functions","06_rejection_examples")
foreach ($c in $cases) {
    Write-Host "=== $c ==="
    python src/main.py --cli "tests/cases/$c/lexer.yal" "tests/cases/$c/grammar.yapar" "tests/cases/$c/input.txt"
}
```

Bash:
```bash
for c in 01_arithmetic_id 02_arithmetic_extended 03_arithmetic_numbers 04_assignments 05_classes_functions 06_rejection_examples; do
    echo "=== $c ==="
    python src/main.py --cli tests/cases/$c/lexer.yal tests/cases/$c/grammar.yapar tests/cases/$c/input.txt
done
```
