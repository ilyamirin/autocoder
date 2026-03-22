# Agent Policy

## Global
- instruction: Prefer the smallest patch that satisfies all acceptance criteria.
- instruction: Do not refactor, restyle, or improve unrelated code.
- instruction: Update only the tests that are directly affected by the task.
- instruction: Reuse existing entities, routes, and patterns before inventing new ones.
- instruction: Avoid broad cleanups unless the task explicitly requires them.

## Area: finance
- instruction: Prefer focused metric or calculation fixes over dataset expansion.
- instruction: Keep financial changes local to the affected computation and tests.

## Area: orders
- instruction: Prefer local table, route, or domain fixes over broad layout rewrites.
- instruction: Preserve existing order statuses and route structure unless the task explicitly changes them.

## Area: dashboard
- instruction: Prefer small dashboard-specific changes over cross-page refactors.
- instruction: Reuse existing cards and metrics before introducing new dashboard structures.

## Area: products
- instruction: Prefer local product table or product domain changes over broad UI redesign.
- instruction: Reuse existing badges, filters, and product attributes where possible.

## Area: platform
- instruction: Prefer the narrowest infrastructure or template change that solves the task.
- instruction: Avoid touching multiple services unless the acceptance criteria clearly require it.

## Area: data
- instruction: Prefer seed-data and test updates over application logic changes.
- instruction: Add the minimum number of new records necessary to satisfy the task.
- instruction: Reuse existing products, brands, and status combinations before creating new ones.
- soft_limit.max_expected_new_records: 2
