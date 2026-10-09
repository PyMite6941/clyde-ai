# Clyde Interface — Tools & Skills Integration

## Purpose
Connect the Clyde interface (design_interface React app) to the tools and skills already built in ~/Clyde/tools/ and ~/Clyde/skills/.

## Available Tools (from ~/Clyde/tools/)

### video/
- ASCII video conversion
- Spectrogram generation
- FFmpeg-based operations
- Integration: Interface can invoke via API calls

### graphics/
- ASCII art generation
- SVG diagram generation
- Infographic layouts (21 layouts × 21 styles)
- Integration: Interface renders AI-generated designs

### browser/
- Web navigation and extraction
- Form automation
- Multi-tab session management
- Integration: Interface uses for web-based design resources

### presentations/
- Slide deck generation (HTML/CSS, PPTX, PDF)
- Design system templates (Stripe, Linear, Vercel style)
- Integration: Core interface functionality

## Skills Integration (from skills_list)

### hermes-agent
- Central coordination skill
- Can invoke other skills
- Interface uses for task delegation
- Load via: skill_view(name='hermes-agent')

### clyde-training-workflow
- Training cycle management
- Status tracking from cron_logs
- Integration: Interface pulls training metrics

### paperclip-service-management
- Paperclip orchestration
- Interface integrates for workflow management
- Load via: skill_view(name='paperclip-service-management')

### creative skills (architecture-diagram, ascii-video, etc.)
- Specific design capabilities
- Interface routes to appropriate skill
- Load via: skill_view(name='skill_name')

## Interface-to-Tool API Contract

### Tool Invocation Pattern
```
POST /api/tools/video/convert
{
  "input": "file.mp4",
  "output": "file.ascii.mp4",
  "options": {"color_scheme": "#FF6B6B,#4ECDC4"}
}

POST /api/tools/graphics/diagram
{
  "type": "architecture",
  "data": {"nodes": [...], "edges": [...]},
  "style": "dark"
}

POST /api/tools/presentations/generate
{
  "sections": 5,
  "topic": "Clyde training summary",
  "color_scheme": "#4ECDC4,#45B7D1,#96CEB4,#FF6B6B"
}
```

### Skill Loading (Python example)
```python
from hermes_tools import skill_view

# Load a skill
skill = skill_view(name='hermes-agent')
# Access its methods, configs, plugins

# Or load specific linked files
references = skill_view(name='clyde-training-workflow', file_path='references/api.md')
```

## Cron Logs Integration

The interface pulls data from `~/Clyde/cron_logs/`:
- `automation_cron.log` — Current run status
- Individual pack logs — Training progress per pack
- `daily_evaluate.log` — Benchmark results
- `previous_cron_output.log` — Historical data

Interface components:
- **Live dashboard** — Real-time training status
- **Historical view** — Past runs and metrics
- **Predictive insights** — Based on training patterns

## Color Scheme System

### User-Provided Schemes
```
Format: "hex1,hex2,hex3,hex4"
Example: "#4ECDC4,#45B7D1,#96CEB4,#FF6B6B"
```

### AI-Generated Schemes
- Based on training data theme
- Complementary color algorithms
- Dark mode optimization (Clyde runs on Pi, likely dark theme)
- Consistent application across all slides/elements

### Application
- Global scheme applied as CSS variables
- Per-element overrides allowed
- Real-time preview in interface
- Export preserves color scheme

## Proposed Interface Sections (AI Focus Areas)

Each section is initially algorithm-locked, then human-editable:

### 1. Training Summary Section
- **AI focus**: Pull from training_status.json
- **Metrics**: loss curves, pack completion, steps
- **Human override**: Rewrite metrics, add commentary
- **Connects to**: ~/Clyde/automation/training_status.json

### 2. Cron Log Insights Section
- **AI focus**: Pull from ~/Clyde/cron_logs/
- **Data**: Training schedule, pack rotation, errors
- **Human override**: Rewrite insights, add annotations
- **Connects to**: ~/Clyde/cron_logs/ files

### 3. Tool Integration Demo Section
- **AI focus**: Showcase video/graphics/browser tools
- **Content**: Before/after examples, usage stats
- **Human override**: Replace with own demos
- **Connects to**: ~/Clyde/tools/ subdirs

### 4. Roadmap & Future Section
- **AI focus**: Proposed features, skill additions
- **Content**: Next steps, improvements wished for
- **Human override**: Complete rewrite of roadmap
- **Connects to**: Skills list, future planning

### 5. Export & Share Section
- **AI focus**: Generate export options
- **Options**: HTML, PPTX, PDF, ASCII video
- **Human override**: Custom export settings
- **Connects to**: Export formats, sharing workflows

## Human Interaction Mechanics

### Drag-and-Drop
- All elements draggable within their section
- Grid-based layout with snap-to-guides
- Per-section or global grid settings
- Undo/redo history maintained

### Chat-to-Rewrite
- User selects any element/text
- Types request: "Make more concise", "Add technical details"
- AI regenerates that specific element
- Maintains color scheme and layout integrity
- Updates across all slides if global element

### Real-Time Preview
- Changes previewed instantly
- Color scheme consistency checked
- Layout validity verified
- Export preview available

### Version History
- Each save creates a version
- Compare versions side-by-side
- Rollback to previous versions
- Export any version

## Technical Implementation Notes

### React Framework (as requested)
- Use create-react-app or Vite
- TypeScript for type safety
- Component-based design
- State management with Context API or Redux
- Responsive design for mobile/desktop

### API Backend (Python/hermes)
- FastAPI or Flask endpoint
- Skill invocation via skill_view()
- Cron log reading (already in place)
- Tool execution (already in ~/Clyde/tools/)
- Authentication: none (local Pi usage) or optional token

### Deployment
- Local: `npm start` on Pi
- Vercel: `vercel deploy` for testing
- Custom domain optional
- Environment variables for config

## Getting Started Checklist

### 1. Interface Setup
- [ ] Create React app in ~/Clyde/interfaces/design_interface/
- [ ] Set up TypeScript config
- [ ] Design component hierarchy
- [ ] Implement color scheme system

### 2. Tool Integration
- [ ] API endpoints for each tools/ subdir
- [ ] Skill loading via skill_view()
- [ ] Cron log data fetching
- [ ] Error handling and fallbacks

### 3. AI Algorithm
- [ ] Section locking mechanism
- [ ] Cooking process (user color scheme + AI generation)
- [ ] Human override logic
- [ ] Version management

### 4. Testing
- [ ] Local testing on Pi
- [ ] Vercel deployment for remote testing
- [ ] Skill loading verification
- [ ] Tool invocation tests

### 5. Deployment
- [ ] Vercel config (vercel.json)
- [ ] Environment variables setup
- [ ] Custom domain (if desired)
- [ ] Monitoring and logs
