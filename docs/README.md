# ORA Automation Documentation

This directory uses the **Diataxis documentation framework** - an industry-standard system for organizing technical documentation by user needs.

## 📐 The Diataxis Framework

Documentation is organized into 4 categories based on **what users need to do**:

| Category | Purpose | When to Use |
|----------|---------|-------------|
| **📚 Guides** | Learning & doing tasks | "How do I...?" |
| **📖 Reference** | Technical specifications | "What does this do?" |
| **🏛️ Explanation** | Understanding concepts | "Why does it work this way?" |
| **📜 History** | Historical records | "What happened?" |

```
Learn a skill → guides/          Need specifics → reference/
Understand why → explanation/    Past events → history/
```

---

## 📁 Directory Structure

### Root-Level Documents
- **[PROJECT_JOURNAL.md](PROJECT_JOURNAL.md)** - Chronological log of all development milestones
- **[PRODUCTION_INCIDENT_LOG.md](PRODUCTION_INCIDENT_LOG.md)** - Critical issues and resolutions
- **README.md** (this file) - Documentation organization guide

---

## 📚 [guides/](guides/)
**Learning-oriented & task-oriented documentation**

Step-by-step instructions for accomplishing specific tasks. These are practical tutorials that teach you how to use the system.

**When to use:** "How do I configure workflows?" "How do I manage orders?"

**Contents:**
- `user-manual.md` - Complete system user guide for daily operations
- `workflow-controls.md` - How to enable/disable and monitor workflows
- `database-operations.md` - How to maintain and operate the database

**Target Audience:** New users, operators, anyone learning to use the system

---

## 📖 [reference/](reference/)
**Information-oriented technical specifications**

Precise technical descriptions of how the system works. Dry, accurate, comprehensive reference material.

**When to use:** "What's the database schema?" "What are the API endpoints?"

**Contents:**
- `database-schema.md` - Complete database structure and relationships
- `requirements.md` - System requirements and specifications
- `api-integration.md` - External API integration specifications
- `authentication-analysis.md` - Authentication system specifications
- `authentication-questionnaire.md` - Auth implementation requirements

**Target Audience:** Developers, architects, anyone who needs precise technical details

---

## 🏛️ [explanation/](explanation/)
**Understanding-oriented conceptual documentation**

Big-picture explanations of why the system is designed the way it is. Helps you understand context and rationale.

**When to use:** "Why use PostgreSQL?" "How does the architecture work?"

**Contents:**
- `project-plan.md` - Overall project strategy and roadmap
- `database-normalization.md` - Why and how the database is normalized
- **`features/`** - Design documents explaining feature architecture:
  - `EOD_EOW_EOM_BUTTON_SYSTEM.md` - Physical inventory control design
  - `UNIFIED_SHIPSTATION_SYNC_PLAN.md` - Sync architecture explanation
  - `OPTIMIZED_POLLING_IMPLEMENTATION_PLAN_V3_FINAL.md` - Polling strategy
  - `WORKFLOW_CONTROL_IMPLEMENTATION_PLAN.md` - Workflow system design
  - And 10 more feature design documents

**Target Audience:** Developers, architects, anyone making design decisions

---

## 📜 [history/](history/)
**Historical records and past remediation**

Documentation of past issues, migrations, and fixes. Preserved for learning and reference.

**When to use:** "How did we migrate to PostgreSQL?" "What was the manual orders issue?"

**Contents:**
- `SQLITE_TO_POSTGRESQL_REMEDIATION_PLAN.md` - Database migration (Oct 2025)
- `MANUAL_ORDERS_COMPLETE_HISTORY.md` - Manual orders remediation
- `REMEDIATION_PLAN.md` - Duplicate order cleanup
- `DUPLICATE_DETECTION_FIX.md` - Detection system fixes
- 11 more historical remediation documents

**Target Audience:** Anyone troubleshooting similar issues, learning from past fixes

---

## 🔍 Quick Navigation

### "I need to learn how to use the system"
→ Start with **`guides/user-manual.md`**

### "I need technical specifications"
→ Check **`reference/`** (database schema, API specs, requirements)

### "I need to understand why it works this way"
→ Read **`explanation/`** (architecture, feature designs, rationale)

### "I need to know what happened in the past"
→ Review **`history/`** (migrations, remediations, incidents)

### "I'm joining the team - where do I start?"
1. `PROJECT_JOURNAL.md` - Project history overview
2. `guides/user-manual.md` - Learn to use the system
3. `reference/requirements.md` - Understand what it does
4. `explanation/project-plan.md` - Understand the strategy
5. `PRODUCTION_INCIDENT_LOG.md` - Learn from past issues

---

## 📝 Documentation Standards

### Where to Put New Docs

| Type of Document | Where It Goes | Example |
|-----------------|---------------|---------|
| How-to guide | `guides/` | "How to configure EOD workflows" |
| API specification | `reference/` | "ShipStation API endpoints" |
| Feature design | `explanation/features/` | "Why we chose watermark-based sync" |
| Bug fix history | `history/` | "October 2025 duplicate order fix" |

### Naming Conventions
- Use lowercase with hyphens for file names: `feature-name.md`
- Exception: Root-level docs use UPPERCASE: `PROJECT_JOURNAL.md`
- Be descriptive: `workflow-controls.md` not `workflows.md`

### Maintenance
- **Active Documentation:** Keep root-level docs up to date
- **Historical Preservation:** Don't delete old docs, move to `history/`
- **Cross-Reference:** Link related documents across categories
- **Update This README:** When adding new major documents

---

## 🎯 The Diataxis Decision Tree

```
What do you need?

├─ Learn to use it → guides/
│  └─ Step-by-step tutorials
│
├─ Look up specifics → reference/
│  └─ Technical specifications
│
├─ Understand concepts → explanation/
│  └─ Architecture & design rationale
│
└─ Review history → history/
   └─ Past issues & migrations
```

---

## 📚 Further Reading on Diataxis

The Diataxis framework is used by:
- Google Cloud Documentation
- Stripe Developer Docs
- Django Documentation
- Many enterprise projects

Learn more: https://diataxis.fr/

---

*Documentation framework: Diataxis*  
*Last Updated: October 2025*
