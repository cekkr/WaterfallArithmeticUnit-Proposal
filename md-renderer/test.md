# Test Markdown File

This is a test file with Mermaid diagrams and LaTeX expressions.

## Mermaid Diagram

```mermaid
graph TD
    A[Start] --> B{Is it working?}
    B -->|Yes| C[Great!]
    B -->|No| D[Debug]
    D --> A
```

## LaTeX Math

Here's an inline equation: $E = mc^2$

And a display equation:

$$\int_{a}^{b} f(x) dx = F(b) - F(a)$$

## Another Mermaid Diagram

```mermaid
sequenceDiagram
    participant User
    participant Script
    participant Mermaid
    User->>Script: Run script
    Script->>Mermaid: Convert diagram
    Mermaid->>Script: Return image
    Script->>User: Show result
```

The quadratic formula: $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$
