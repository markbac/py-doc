---
title: Interface samples
subtitle: API specifications and a use case diagram in one document
author: A. Writer
date: 2026-10-16
version: "1.0"
status: Draft
classification: Public
document_number: EX-IF-001
description: Interface specifications for a sample library system, included from their own files.
---

# Interface samples

This document is separate from the SN-100. It describes a sample library system, and shows how to
keep interface specifications in their own files and include them in a document. Each
specification is pulled in with a code include, so the document always shows the file as it is in
the repository. The language of each code block comes from the file's extension.

| File | Format | What it describes |
|---|---|---|
| `includes/apis/library-openapi.yaml` | OpenAPI 3.1 | The HTTP API: books, users and webhooks, with paging, filters and OAuth2 |
| `includes/apis/library-asyncapi.yaml` | AsyncAPI 2.0 | The events published over MQTT when books are added, checked out or returned |
| `includes/apis/library.proto` | Protocol Buffers (gRPC) | The same operations as gRPC calls |
| `includes/apis/library.graphql` | GraphQL | The same data as a GraphQL schema |

[[CAPTION:Table]] The interface files

## Use cases

[[CAPTION:Figure]] Who uses a banking system, and for what
```plantuml
@startuml
left to right direction
actor Customer
actor "Bank Employee" as BankEmployee
actor "Third-Party Payment Service" as ThirdParty

rectangle "Banking system" {
  usecase "View Account Details" as U1
  usecase "Transfer Funds" as U2
  usecase "Pay Bills" as U3
  usecase "Request Loan" as U4
  usecase "Manage Beneficiaries" as U5
  usecase "Customer Support" as U6
  usecase "Generate Account Statement" as U7
  usecase "View Loan Status" as U8
}

Customer -- U1
Customer -- U2
Customer -- U3
Customer -- U5
Customer -- U7
Customer -- U8
BankEmployee -- U4
BankEmployee -- U6
U3 -- ThirdParty
@enduml
```

## HTTP API

[[CAPTION:Figure]] The OpenAPI description
[[INCLUDE-CODE: includes/apis/library-openapi.yaml]]

## Events

[[CAPTION:Figure]] The AsyncAPI description
[[INCLUDE-CODE: includes/apis/library-asyncapi.yaml]]

## gRPC service

[[CAPTION:Figure]] The Protocol Buffers definition
[[INCLUDE-CODE: includes/apis/library.proto]]

## GraphQL schema

[[CAPTION:Figure]] The GraphQL schema
[[INCLUDE-CODE: includes/apis/library.graphql]]
