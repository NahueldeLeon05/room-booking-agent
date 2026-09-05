# Overview
<!-- Summarize the tool contracts documented in this file. -->

## Tool inventory
<!-- List each available tool and its intended use. -->

## Schemas
<!-- Define the input and output schema for each tool. -->

## Tool return format

### Arguments vs return values

Tool arguments and return values have different purposes. Arguments use structured JSON because the application needs to parse them. Return values are read by the model.

### Decision

I decided to return structured and consistent text instead of JSON. Each tool uses the same format and includes the booking ID when it is needed.

### Rationale

Text uses fewer tokens and gives the model less work before answering the user. It is also consistent with the conversational interface decision in [04-architecture.md](04-architecture.md).

### Trade-off considered

Short and flat JSON would also work. The problem appears with deeply nested JSON and long responses. JSON would be better if the model needed to make precise calculations with the data, but the service already does that work here.

## Error responses
<!-- Define the error shapes and actionable information returned by tools. -->

## Security considerations
<!-- Document authentication, authorization, and data-handling requirements. -->
