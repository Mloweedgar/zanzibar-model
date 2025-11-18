# AI Model Analysis Prompt Template

Use this prompt when you need an AI to deeply analyze a codebase and explain it comprehensively for presentations, onboarding, or documentation.

---

## 📋 FULL PROMPT (Copy & Paste)

```
I need you to comprehensively analyze this codebase and create a complete understanding guide. I have a [presentation/meeting/review] [tomorrow/soon] and need to understand the model/system end-to-end.

Please:

1. **READ KEY FILES** - Start with:
   - README.md (overview, usage)
   - Main entry point (main.py, app.py, index.js, etc.)
   - requirements.txt / package.json (dependencies)
   - Any deliverables/ or docs/ folders

2. **ANALYZE ARCHITECTURE** - Understand:
   - What is the high-level purpose? (1-sentence summary)
   - What are the main components/modules?
   - What is the data flow? (input → processing → output)
   - What are the key algorithms or models?
   - What are the core mathematical equations or business logic?

3. **DEEP DIVE CODE** - Examine:
   - Core computational modules (where the "work" happens)
   - Configuration files (parameters, settings)
   - Data pipeline (how data flows through the system)
   - Calibration/validation logic (if applicable)
   - Visualization/dashboard components (if applicable)

4. **IDENTIFY KEY CONCEPTS** - Extract:
   - Domain-specific terminology (with plain-English explanations)
   - Critical parameters and their typical values
   - Input data requirements and formats
   - Output data structures and interpretation
   - Model assumptions and limitations

5. **CREATE COMPREHENSIVE GUIDE** - Generate a markdown document with:
   
   a) **Executive Summary** (30-second elevator pitch)
   
   b) **Architecture Overview** (high-level diagram in text/pseudocode)
   
   c) **Component Deep-Dives** - For each major module:
      - Purpose and role
      - Key functions/classes
      - Core equations (with examples)
      - Code locations (file, function, line ranges)
   
   d) **Data Pipeline** (complete input→output flow with file paths)
   
   e) **Key Findings/Results** (if there are outputs or analysis results)
   
   f) **Running the System** (quick reference commands)
   
   g) **Presentation Talking Points** (key statistics, insights to highlight)
   
   h) **Q&A Preparation** (anticipated questions with detailed answers)
   
   i) **Glossary** (domain terms explained for non-experts)
   
   j) **Limitations & Assumptions** (what the model doesn't do)

6. **STYLE REQUIREMENTS**:
   - Write for TWO audiences: technical developers AND non-technical stakeholders
   - Use analogies and real-world examples for complex concepts
   - Include specific numbers, statistics, and quantitative results
   - Provide code snippets with explanatory comments
   - Create "Presenter Guidance" callout boxes with simplified explanations
   - Add a pre-presentation checklist at the end

7. **FOCUS AREAS** (customize based on your needs):
   - [ ] Mathematical models and equations
   - [ ] Machine learning algorithms
   - [ ] Data processing pipelines
   - [ ] API integrations
   - [ ] Database schemas
   - [ ] Performance optimizations
   - [ ] Testing and validation
   - [ ] Deployment architecture

Please start by reading the README and main entry point, then work through the codebase systematically. Make liberal use of parallel tool calls to read multiple files simultaneously.

Generate the guide as a single comprehensive markdown file.
```

---

## 🎯 CUSTOMIZATION OPTIONS

Adjust the prompt based on your specific needs:

### For Machine Learning Projects
Add this section:
```
Additional ML-specific requirements:
- Training vs inference pipelines
- Model architecture details
- Hyperparameters and tuning
- Evaluation metrics and results
- Data preprocessing steps
- Feature engineering logic
```

### For Web Applications
Add this section:
```
Additional web-specific requirements:
- Frontend architecture (components, state management)
- Backend API structure (endpoints, authentication)
- Database schema and relationships
- User flows and interactions
- Deployment and infrastructure
```

### For Data Pipelines
Add this section:
```
Additional pipeline-specific requirements:
- ETL/ELT process stages
- Data validation and quality checks
- Error handling and retry logic
- Scheduling and orchestration
- Monitoring and alerting
```

### For Scientific/Research Code
Add this section:
```
Additional research-specific requirements:
- Scientific methodology and theory
- Validation against published results
- Reproducibility considerations
- Parameter sensitivity analysis
- Comparison to alternative approaches
```

---

## 📝 EXAMPLE OUTPUT STRUCTURE

The AI should generate something like this:

```markdown
# [PROJECT NAME] - Complete Understanding Guide

## 🎯 EXECUTIVE OVERVIEW
[30-second pitch]

## 📊 ARCHITECTURE OVERVIEW
[Component diagram in text]

## 🔬 MODULE 1: [NAME]
### Purpose
### Core Equation
### Example Calculation
### Code Location

## 🔬 MODULE 2: [NAME]
[Same structure...]

## 🗂️ DATA PIPELINE
[Input files → Processing → Output files]

## 📈 KEY FINDINGS
[Statistics and results table]

## 💻 RUNNING THE SYSTEM
[Command reference]

## 📊 PRESENTATION TALKING POINTS
[Slide-by-slide guidance]

## ❓ Q&A PREPARATION
[Questions & detailed answers]

## 🎓 GLOSSARY
[Terms defined]

## 🔍 LIMITATIONS & ASSUMPTIONS
[What it doesn't do]

## ✅ PRE-PRESENTATION CHECKLIST
[Action items]
```

---

## 🚀 ADVANCED USAGE TIPS

### 1. **For Large Codebases**
If the codebase is too large for a single pass:
```
Phase 1: "First, create a high-level architecture map with main modules"
Phase 2: "Now deep-dive into module X specifically"
Phase 3: "Now analyze the data pipeline end-to-end"
```

### 2. **For Legacy/Undocumented Code**
Add this:
```
This codebase has minimal documentation. Please:
- Infer purpose from code structure and variable names
- Identify coding patterns and conventions
- Highlight areas that need refactoring or better documentation
- Create the documentation that SHOULD exist
```

### 3. **For Performance-Critical Systems**
Add this:
```
Focus on performance aspects:
- Computational complexity of key algorithms
- Bottlenecks and optimization opportunities
- Memory usage patterns
- Parallelization strategies
- Caching mechanisms
```

### 4. **For Time-Constrained Scenarios**
```
I have [X hours] until my presentation. Prioritize:
1. High-level architecture (20% of time)
2. Core business logic (40% of time)
3. Key results/statistics (30% of time)
4. Q&A preparation (10% of time)

Skip: detailed code walkthroughs, minor utilities, test files
```

---

## 🔧 TROUBLESHOOTING

### If AI's output is too technical:
Add: "Explain everything as if presenting to non-technical executives"

### If AI's output is too shallow:
Add: "Provide code examples and mathematical derivations for all key concepts"

### If AI misses key files:
List them explicitly: "Make sure to analyze: [file1.py, file2.py, ...]"

### If output is too long:
"Create two versions: (1) Executive summary (5 pages), (2) Technical deep-dive (full detail)"

---

## 📚 FOLLOW-UP PROMPTS

After receiving the initial guide, use these for clarification:

```
"Explain the [SPECIFIC CONCEPT] in more detail with a worked example"

"What would happen if I changed [PARAMETER] from X to Y?"

"Walk me through exactly what happens when [SPECIFIC FUNCTION] is called"

"Create a diagram showing the data flow through [MODULE]"

"What are the top 3 most important things for my presentation?"

"Generate a 5-minute presentation script based on this guide"

"What questions am I most likely to get asked, and how should I answer them?"
```

---

## ✅ QUALITY CHECKLIST

A good AI-generated guide should have:

- [ ] Clear 30-second executive summary
- [ ] Architecture diagram or textual equivalent
- [ ] Specific code locations (file, function, line numbers)
- [ ] Mathematical equations with worked examples
- [ ] Real numbers and statistics (not just placeholders)
- [ ] Plain-English explanations of technical concepts
- [ ] Analogies for complex ideas
- [ ] Presentation talking points
- [ ] Anticipated Q&A
- [ ] Glossary of domain terms
- [ ] Command reference for running the system
- [ ] Pre-presentation checklist

---

## 🎯 SUCCESS CRITERIA

You'll know the guide is good when:

1. **Completeness**: You can explain the entire system without looking at code
2. **Clarity**: A non-technical person understands the overview
3. **Depth**: A technical person can dive into implementation details
4. **Actionability**: You have talking points ready for your presentation
5. **Confidence**: You can answer "how does this work?" for any component

---

**Template version:** 1.0  
**Created:** October 7, 2025  
**Use case:** Pre-presentation codebase analysis

---

## 📖 REAL-WORLD EXAMPLE

Here's how this prompt was used for the Zanzibar FIO model:

**Input:** "I need to understand this FIO pathogen model for a presentation tomorrow"

**AI Actions:**
1. Read README.md, main.py, requirements.txt (parallel)
2. Analyzed fio_config.py (parameters), fio_core.py (Layer 1), fio_transport.py (Layers 2-3)
3. Examined fio_runner.py (orchestration), calibrate.py (validation)
4. Reviewed dashboard.py (visualization), technical report (results)

**Output:** 50-page comprehensive guide covering:
- 3-layer model architecture (source → transport → dilution)
- Mathematical equations with worked examples
- Code locations for every major function
- Key findings (84.9% of private wells exceed safety threshold)
- Presentation talking points ("Private wells 57× more contaminated")
- Q&A prep ("Why only 3 calibration points?")
- Pre-presentation checklist

**Time:** ~15 minutes from prompt to full guide
**Result:** Presenter felt fully prepared for technical audience

---

*Copy the main prompt above and customize for your specific needs!*
