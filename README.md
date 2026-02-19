# AI and Distributional Policy Research

A PolicyEngine research initiative examining how economic policies mediate the relationship between AI-driven economic shocks and distributional outcomes.

## Overview

This microsite outlines PolicyEngine's interest in modeling the causal chain: **AI economic shocks → policy interventions → distributional outcomes** (income, consumption, wealth). Rather than forecasting AI's economic impacts or prescribing optimal policies, we provide a framework for analyzing how different policy responses shape distributional outcomes under AI-driven economic change.

## Research Questions

- How do economic policies (taxes, transfers, UBI proposals) mediate AI's impact on income, consumption, and wealth distribution?
- How would current policies vs. alternatives (UBI, expanded safety nets, capital taxation) differentially shape distributional outcomes under AI scenarios?
- What are the inequality, poverty, and work incentive effects of different policy responses to AI economic shocks?
- How do these mediation effects vary across regions, demographics, and AI trajectories?

## Key Features

This site includes:

1. **Research Overview**: The challenge, our approach, and why this matters
2. **Relevant Research**: Summary of academic work on AI economics, labor impacts, inequality, and microsimulation
3. **Policy Scenarios**: Different policy designs to evaluate (current policy, UBI, safety net expansion, capital taxation, hybrid approaches)
4. **Technical Requirements**: What's needed to conduct this research (scenario modeling, data, computational infrastructure, validation)
5. **Potential Stakeholders**: Organizations that might be interested in supporting or collaborating on this work

## Geographic Scope

While initial work would focus on the United States using [PolicyEngine-US](https://policyengine.org/us), this research framework could be expanded to:

- **United Kingdom** ([PolicyEngine-UK](https://policyengine.org/uk)) - fully operational
- **Canada** ([PolicyEngine-Canada](https://policyengine.org/ca)) - partially developed
- Other countries where PolicyEngine models are available

Cross-country comparisons would provide valuable insights into how different tax-benefit systems respond to AI-driven economic change.

## Development

### Prerequisites

- Node.js >= 22.0.0
- npm

### Installation

```bash
make install
```

Or:

```bash
npm ci
```

### Running the Development Server

```bash
make debug
```

Or:

```bash
npm start
```

The site will be available at `http://localhost:3000`.

### Building for Production

```bash
make build
```

Or:

```bash
npm run build
```

### Testing

```bash
make test
```

Or:

```bash
npm test
```

### Code Formatting

Before committing, always format your code:

```bash
make format
```

Or:

```bash
npm run lint -- --fix && npx prettier --write .
```

## Project Structure

```
ai-inequality/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Hero.js              # Landing section
│   │   ├── Hero.css
│   │   ├── Overview.js          # Research overview
│   │   ├── Research.js          # Research summary
│   │   ├── PolicyScenarios.js   # Policy scenarios
│   │   ├── TechnicalRequirements.js
│   │   ├── Stakeholders.js      # Organizations
│   │   ├── Footer.js
│   │   └── Footer.css
│   ├── App.js                   # Main app component
│   ├── App.css
│   ├── index.js                 # Entry point
│   └── index.css
├── package.json
├── Makefile
└── README.md
```

## Live Site

**https://policyengine.github.io/ai-inequality/**

The site automatically deploys to GitHub Pages on every push to `main`.

## Contributing

This is a PolicyEngine project. Please follow the guidelines in [CLAUDE.md](../CLAUDE.md) for development practices:

1. Use functional React components with hooks
2. Run `make format` before committing
3. Test your changes with `npm test`
4. Ensure linting passes with `npm run lint -- --max-warnings=0`

## Contact

Interested in collaborating on this research?

- Email: [hello@policyengine.org](mailto:hello@policyengine.org)
- Website: [https://policyengine.org](https://policyengine.org)
- GitHub: [https://github.com/PolicyEngine](https://github.com/PolicyEngine)

## License

AGPL-3.0

## About PolicyEngine

PolicyEngine is a nonprofit building open-source tax-benefit microsimulation models to make public policy more transparent, accessible, and impactful.
