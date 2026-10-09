# Clyde TODO — Remaining Work Items

## High Priority

### Model Routing Configuration
- [ ] Set up 3-5 model routing across OpenRouter, Groq, NVIDIA providers
- [ ] Configure model selection per domain (coding, math, design, analysis)
- [ ] Implement fallback chain when primary provider hits rate limits
- [ ] Test model inference speeds and costs per task type

### Interface Development
- [ ] Complete design_interface React app setup (refer to interfaces/design_spec.md)
- [ ] Implement API endpoints for tool invocation (video, graphics, browser, presentations)
- [ ] Build color scheme system integration (user-provided hex schemes)
- [ ] Create drag-and-drop section routing within interface sections
- [ ] Implement human override logic for AI-generated sections

### Training Pipeline
- [ ] Verify clyde_train_cycle.sh works with Python 3.13 (fix JSON compatibility)
- [ ] Test data pack switching (english → tool-use-citations → etc.)
- [ ] Validate guardrails against prohibited content patterns
- [ ] Test resume patterns (same track new pack, resume from checkpoint)
- [ ] Append 14 new Q&A pairs across tool-use-citations, fact-checking, boundary-aware

### Cron Job Verification
- [ ] Test manual run: `/home/pymite6941/Clyde/automation/clyde_train_cycle.sh --pack english --track A`
- [ ] Verify crontab schedules execute correctly
- [ ] Check log output destinations (cron_logs/ vs automation/cron_output.log)
- [ ] Test daily evaluation at 19:00 and python fallback at 20:00

### Git & Repository
- [ ] Push to GitHub with proper .gitignore protections
- [ ] Verify training_data/ and cron_logs/ are gitignored
- [ ] Confirm only interface/framework files are tracked remotely
- [ ] Set up GitHub Actions or manual workflow for updates

## Medium Priority

### Documentation Gaps
- [ ] Expand CRON_LOG_GUIDE.md with troubleshooting checklist
- [ ] Add model routing configuration docs to README.md
- [ ] Document interface API contract endpoints
- [ ] Create quick-start checklist for new pack setup
- [ ] Document guardrail patterns and how to add new approved packs

### Skill Enhancements
- [ ] Add model routing skill to Hermes Agent profiles
- [ ] Create automated status report generation
- [ ] Build pack expansion workflow (append Q&A, update data_version)
- [ ] Create evaluation metric comparison between models

### Testing & QA
- [ ] Test all 7 packs through full training cycle
- [ ] Verify sample interface HTML renders correctly
- [ ] Test model routing under rate limiting conditions
- [ ] Validate guardrail false positive/negative rates

## Low Priority

### Feature Ideas
- [ ] Add Track B (Qwen 0.5B + LoRA) support
- [ ] Implement Kaggle dataset auto-upload workflow
- [ ] Create export/share sections (HTML, PPTX, PDF, ASCII video)
- [ ] Build predictive insights from training patterns
- [ ] Add real-time resource monitoring (Pi CPU temp, RAM)

### Cleanup
- [ ] Remove __pycache__ directories from git tracking
- [ ] Consolidate any duplicate automation scripts
- [ ] Review and prune old cron log entries
- [ ] Verify .gitignore covers all sensitive paths

## Done (from recent commit)

- [x] Git commit d6f9d1a — interfaces + training foundation
- [x] .gitignore updated — training_data/, cron_logs/, automation runtime logs protected
- [x] CRON_LOG_GUIDE.md — documents cron output directory structure
- [x] Interface docs committed — design_spec.md, interface_guide.md, sample_interface.html
- [x] Automation scripts committed — manager, evaluate, guardrails, notebook update
- [x] Tools SKILL.md + submodule READMEs committed
- [x] README.md — created with architecture, model strategy, git protection overview