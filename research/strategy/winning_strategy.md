# Winning Strategy — Deep Agents Hackathon

## The Formula (based on judge analysis + past winners)

### 1. Use as many sponsor APIs as possible — meaningfully
Judges are representatives of sponsors. They WANT to see their tech used well.
- **Anthropic Claude** = agent brain (reasoning, planning, tool use)
- **Bland AI** = voice interface (2/4 judges are Bland!) — THIS IS THE HIGHEST PRIORITY INTEGRATION
- **AWS** = infrastructure (1/4 judges is AWS SA of the Year)
- **Aerospike** = agent memory / vector search
- **Okta** = secure agent identity
- **Airbyte** = data ingestion pipeline

Ideal project integrates at least 4-5 of these meaningfully.

### 2. Solve a SPECIFIC, real business problem
Past winners all targeted a narrow, real-world pain point:
- RivalMap → competitive intelligence for sales teams
- PitchScoop → pitch coaching for founders
- ArgusSquared → regulatory compliance for code reviews
- fridaySRE → incident response for DevOps

DON'T build: generic chatbot, general-purpose assistant, "AI for everything"
DO build: a tool for a specific persona solving a specific workflow

### 3. Show deep autonomous behavior
This is literally called "Deep Agents". The agent must:
- Plan multi-step tasks autonomously
- Use tools to gather information
- Make decisions based on gathered info
- Execute actions (not just suggest)
- Handle failures and retry with different approaches
- Show the reasoning chain (Abdul Rahim cares about observability)

### 4. Make the demo unforgettable
- 3-minute demo window (based on past events)
- Start with the PROBLEM, not the tech
- Show a LIVE demo, not slides
- Have a fallback recording in case of technical issues
- Show the agent reasoning in real-time (traces/logs visible)
- End with impact: "This saves X hours / Y dollars"

### 5. Polish the UX
Spencer Small (Bland Head of Eng) has an architecture degree from Brown.
He cares about design. Make the UI clean and professional.
- Use a good frontend framework (Next.js, etc.)
- Have a clean dashboard showing agent state
- Visualization of agent reasoning steps
- Professional branding (name, logo, color scheme)

### 6. Add observability (for Abdul Rahim)
Abdul is building AgentBasis — an agent observability tool. He will LOVE seeing:
- Step-level traces of agent actions
- Tool call visibility
- Decision path visualization
- Cost/latency metrics
- Failure detection and handling

---

## Pre-hackathon Checklist

### Before the event:
- [ ] Choose project idea (specific problem + persona)
- [ ] Set up Claude API integration (tool use, system prompts)
- [ ] Set up Bland AI API integration (voice agent boilerplate)
- [ ] Set up AWS account and deploy pipeline (Lambda, Bedrock, etc.)
- [ ] Set up Aerospike for agent state/memory
- [ ] Set up Okta developer account
- [ ] Set up Airbyte connectors
- [ ] Build basic UI shell (Next.js or similar)
- [ ] Build agent observability dashboard (trace viewer)
- [ ] Prepare demo script and talking points
- [ ] Create fallback demo recording

### Day-of timeline:
| Time | Action |
|------|--------|
| 9:30-11:00 | Set up, listen to keynotes, finalize plan |
| 11:00-12:30 | Core agent logic + Claude integration |
| 12:30-1:30 | Bland AI voice integration + lunch |
| 1:30-3:00 | AWS deployment + Aerospike memory + polish |
| 3:00-4:00 | End-to-end testing, bug fixes, UI polish |
| 4:00-4:30 | Prepare demo, record backup video |
| 5:00+ | Present |

---

## Risk Mitigation
1. **API keys**: Get ALL sponsor API keys set up and tested BEFORE the event
2. **Fallback**: If voice doesn't work, text-based is fine — but try voice first
3. **Scope**: Better to have 1 working flow than 5 broken features
4. **WiFi**: Have mobile hotspot as backup
5. **Demo**: Pre-record a backup demo video
