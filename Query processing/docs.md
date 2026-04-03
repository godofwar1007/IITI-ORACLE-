# 📘 Query Preprocessing Pipeline – Technical Documentation

---

# 1. 🎯 The Challenge

Students interact with AI systems using:

* Informal language ("midsem kab hai")
* Abbreviations ("lhc", "erp")
* Noisy input ("cs204d midsem??")

These queries:

* Lack structure
* Contain ambiguous tokens
* Perform poorly in retrieval systems

---

# 2.  Design Philosophy

The system is built on three principles:

### 1. Meaning Preservation

Do not distort user intent.

### 2. Minimal Expansion

Avoid token explosion — only clarify meaning.

### 3. Structured Transformation

Convert unstructured queries into machine-understandable form.

---

# 3. ⚙️ Pipeline Architecture

```text
Raw Query
   ↓
[1] Cleaning
   ↓
[2] Course Parser (Entity Extraction)
   ↓
[3] Jargon Mapping (Normalization)
   ↓
[4] Query Expansion (Meaning Clarification)
   ↓
[5] Multi-query Generation (LLM)
```

---

# 4.  Component Breakdown

---

## 4.1 Cleaning Layer

### Purpose

Normalize raw text and remove noise.

### Operations

* Lowercasing
* Removing special characters
* Normalizing whitespace

### Example

```
"CS-204 (A) midsem!!!"
→ "cs 204 midsem"
```

---

## 4.2 Course Parser

### Purpose

Extract structured course entities.

### Technique

Regex-based pattern detection:

```
[A-Z]{2,3} + digits
```

### Example

```
"cs 204 midsem"
→ CS204
```

---

## 4.3 Jargon Mapping

### Purpose

Map informal campus terms → canonical forms.

### Examples

| Input  | Canonical |
| ------ | --------- |
| midsem | MSE       |
| lhc    | LHC       |
| erp    | ERP       |

---

## 4.4 Query Expansion (Key Innovation)

### Problem

Traditional expansion adds too many tokens → semantic drift.

### Solution

**Bracket-based minimal expansion**

### Rule

```
jargon → JARGON (full meaning)
```

### Example

```
midsem → MSE (mid semester examination)
lhc → LHC (lecture hall complex)
```

### Result

```
CS204 MSE (mid semester examination) SYLLABUS
```

---

## 4.5 Multi-query Generation (Groq)

### Purpose

Improve retrieval recall by generating diverse query variations.

### Model

LLaMA3 via Groq API

### Example Output

```
1. CS204 mid semester exam syllabus
2. Design and Analysis of Algorithms syllabus
3. CS204 internal exam topics
```

---

# 5. 🔄 End-to-End Flow

### Input

```
cs 204 midsem syllabus
```

### Output

```
Expanded Query:
CS204 MSE (mid semester examination) SYLLABUS

Multi Queries:
- CS204 mid semester exam syllabus
- Algorithms midterm syllabus
- CS204 internal exam topics
```

---

# 6.  Testing Strategy

### 1. Unit Testing

Each module tested independently:

* clean
* parser
* expansion

### 2. Pipeline Testing

End-to-end validation using test queries

### 3. Behavioral Testing

Real student queries:

* slang
* typos
* mixed intent

---

# 7. ⚠️ Challenges Faced

### 1. Over-expansion

Initial approach added too many tokens → reduced quality

### 2. Ambiguous Queries

Handled via multi-query generation

### 3. Noisy Input

Solved using cleaning + regex parsing

---

# 8. 🚀 Future Improvements

* Embedding-based query understanding
* Intent classification layer
* Auto-learning jargon dictionary

---

# 9.  Key Insight

> In retrieval systems:
> **Precision > verbosity**

Minimal, meaningful expansion outperforms aggressive expansion.

---

# 10. 📌 Conclusion

This system acts as a **bridge between human queries and machine retrieval systems**, ensuring:

* semantic clarity
* structured representation
* improved retrieval performance
