# Launching Crisis Room: A Production Incident Response RL Environment

In the high-stakes world of SRE and DevOps, every second counts when a production system goes down. But how do we train agents—or even human engineers—to navigate the "fog of war" during a live incident? Enter **Crisis Room**, a new reinforcement learning (RL) environment designed to simulate real-world production outages.

## The Vision: Training for the "Fog of War"
The `crisis_room` environment isn't just about clicking buttons; it's about **investigation**. When an episode begins, the agent is dropped into a simulated crisis with nothing but a vague incident title and a set of firing alerts. To succeed, the agent must interact with a sophisticated state machine, performing actions like:

* **check_logs**: Reviewing service logs for 500 errors or timeout patterns.
* **run_diagnostic**: Running specific checks like `db_connections` or `ssl_check`.
* **restart_service** / **rollback_deployment**: Executing the technical fix once the root cause is identified.
* **notify_team** / **escalate**: Managing the human side of the incident response.

## How It Works: The Tech Stack
Built with **FastAPI** and **Pydantic**, Crisis Room follows the OpenEnv standard, exposing a clean HTTP API for agents to interact with. Under the hood, the environment manages a global session that tracks every move an agent makes.

### Shaping the Reward
We didn't want a simple binary "success or failure" reward. Instead, we implemented a **Shaped Reward Function** ([0, 1]) that encourages professional behavior:
1.  **Resolution (40%)**: Did you actually fix the affected services?
2.  **Investigation (30%)**: Did you look at the logs and diagnostics before acting?
3.  **Efficiency (20%)**: How fast did you solve it within the step budget?
4.  **Communication (10%)**: Did you remember to notify the team?

*Note: Just like in real life, there are penalties. Redundant actions or restarting the wrong service will dock your score.*

## Difficulty Tiers
Crisis Room offers three levels of challenges to test the limits of your RL models:

### Easy Mode
* Step Budget: 8 Steps
* Visibility: Full logs listed at start

### Medium Mode
* Step Budget: 10 Steps
* Visibility: Full logs listed at start

### Hard Mode
* Step Budget: 12 Steps
* Visibility: No hints; you must know which services to check

From **Database Connection Pool exhaustion** to **Silent Data Corruption** in a pricing service, these incidents are modeled after real architectural failures.

## Results and Performance
We evaluated our environment using high-parameter LLMs (like Qwen2.5-72B) via our `inference.py` runner. By analyzing the **Episode Max Reward**, we can determine if the agent is learning to investigate or simply guessing. Our baseline tests show that while "Easy" incidents are solvable with basic logic, "Hard" incidents require a nuanced understanding of cascading failures.

## Get Involved
We are excited to see how the community uses Crisis Room to push the boundaries of automated SRE agents. All resources are available below:

* **Code Repository**: [Insert your repo link here]
* **Colab Notebook**: [Insert your Colab link here]
* **Hugging Face Space**: [Insert your Space link here]

---
*This project was submitted for the Campus RL Challenge. Deadline: April 26, 5:00 PM.*
