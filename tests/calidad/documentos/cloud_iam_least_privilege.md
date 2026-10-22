# Least Privilege in Cloud Identity and Access Management

## The principle
The principle of least privilege states that every user, service, or application should receive only the permissions it needs to perform its task, and nothing more. It limits the damage an attacker can cause with stolen credentials.

## Roles and policies
Cloud providers group permissions into roles, and policies assign those roles to identities. Broad predefined roles, such as an administrator role, are convenient but usually grant far more access than a workload requires. Custom roles let teams grant a narrower set of actions.

## Service accounts
Applications authenticate with service accounts instead of personal user accounts. Each workload should have its own service account, so that permissions can be scoped to that workload and revoked without affecting others.

## Temporary credentials
Long-lived access keys are a common source of breaches when they leak into code repositories. Temporary credentials expire automatically after a short period, which reduces the window in which a leaked credential can be used.

## Reviewing permissions
Permissions tend to accumulate over time. Regular access reviews remove permissions that are no longer used, and access logs help identify which permissions each identity actually exercises.
