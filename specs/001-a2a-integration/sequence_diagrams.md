# tau2-bench Evaluation Sequence Diagrams

This document illustrates the sequence of interactions for `tau2-bench` evaluations, focusing on the A2A (Agent-to-Agent) integration, sync-async bridges, and threading models.

## High-Level Overview

This diagram shows the overall flow where a Platform (or User) requests an evaluation from `tau2_agent`, which then orchestrates the evaluation by communicating with the Evaluatee (e.g., `simple_nebius_agent`) via A2A.

```mermaid
sequenceDiagram
    participant Platform as Platform Simulation
    participant Evaluator as tau2_agent (Evaluator)
    participant Evaluatee as simple_nebius_agent (Evaluatee)

    Note over Platform, Evaluatee: Agent Discovery Phase
    Platform->>Evaluator: GET /.well-known/agent-card.json
    Evaluator-->>Platform: Agent Card (Capabilities)
    Platform->>Evaluatee: GET /.well-known/agent-card.json
    Evaluatee-->>Platform: Agent Card (Capabilities)

    Note over Platform, Evaluatee: Evaluation Phase
    Platform->>Evaluator: POST /a2a/tau2_agent (Run Evaluation)
    
    loop Evaluation Loop (Multiple Tasks)
        Evaluator->>Evaluatee: POST /a2a/simple_nebius_agent (User Message)
        Evaluatee-->>Evaluator: Response (Tool Call or Text)
        
        opt Tool Execution
            Evaluator->>Evaluator: Execute Tool (if needed)
            Evaluator->>Evaluatee: POST /a2a/simple_nebius_agent (Tool Result)
            Evaluatee-->>Evaluator: Response
        end
    end

    Evaluator-->>Platform: Evaluation Results (JSON)
```

## Detailed Flow: Sync-Async Bridge & Threading

This diagram details the internal architecture, highlighting how `tau2_agent` handles the synchronous `tau2-bench` core logic within an asynchronous ADK environment using threading and sync-async bridges.

**Key Components:**
*   **ADK Main Loop**: The asynchronous event loop handling incoming HTTP requests.
*   **RunTau2Evaluation**: The tool implementation that bridges to the synchronous domain runner.
*   **Thread Pool**: Used to run the blocking `run_domain` logic without freezing the ADK server.
*   **A2AAgent**: The synchronous agent wrapper used by `tau2-bench`.
*   **Sync-Async Bridge**: A mechanism in `A2AAgent` to call async HTTP clients from synchronous code.

```mermaid
sequenceDiagram
    participant Platform as Platform
    box "tau2_agent (Evaluator)" #f9f9f9
        participant ADK as ADK Main Loop (Async)
        participant Tool as RunTau2Evaluation (Async)
        participant Thread as Thread Pool (Sync)
        participant Runner as run_domain (Sync)
        participant A2AAgent as A2AAgent (Sync)
        participant Bridge as Sync-Async Bridge
        participant Client as A2AClient (Async)
    end
    participant Evaluatee as simple_nebius_agent

    Platform->>ADK: POST /a2a/tau2_agent (Request Evaluation)
    ADK->>Tool: run_async()
    
    Note right of Tool: Offload blocking logic to thread<br/>to prevent ADK loop starvation
    Tool->>Thread: loop.run_in_executor(run_domain)
    
    activate Thread
    Thread->>Runner: run_domain(config)
    activate Runner
    
    loop Simulation Steps
        Runner->>A2AAgent: generate_next_message()
        activate A2AAgent
        
        Note right of A2AAgent: A2AAgent is Sync, but needs Async HTTP.<br/>Uses Bridge to handle nested loops.
        A2AAgent->>Bridge: _async_generate()
        activate Bridge
        
        Bridge->>Client: send_message()
        activate Client
        Client->>Evaluatee: POST /a2a/simple_nebius_agent
        Evaluatee-->>Client: Response
        Client-->>Bridge: Response Content
        deactivate Client
        
        Bridge-->>A2AAgent: AssistantMessage
        deactivate Bridge
        
        A2AAgent-->>Runner: AssistantMessage
        deactivate A2AAgent
    end
    
    Runner-->>Thread: Evaluation Results
    deactivate Runner
    Thread-->>Tool: Results
    deactivate Thread
    
    Tool-->>ADK: Tool Output (JSON)
    ADK-->>Platform: Final Response
```

## A2A Client Connection Lifecycle

This diagram shows how `A2AClient` manages HTTP connections to ensure reliability and avoid event loop conflicts.

```mermaid
sequenceDiagram
    participant Caller as A2AAgent / Bridge
    participant Client as A2AClient
    participant HTTP as httpx.AsyncClient
    participant Remote as Remote Agent

    Caller->>Client: send_message(content)
    activate Client
    
    Note right of Client: Create fresh client per request<br/>to avoid event loop binding issues
    Client->>Client: _create_http_client()
    Client->>HTTP: __aenter__()
    activate HTTP
    
    Client->>HTTP: post(url, json=payload)
    HTTP->>Remote: HTTP POST
    Remote-->>HTTP: HTTP 200 OK
    HTTP-->>Client: Response
    
    Client->>HTTP: __aexit__()
    deactivate HTTP
    Note right of HTTP: Connection closed
    
    Client-->>Caller: Result
    deactivate Client
```
