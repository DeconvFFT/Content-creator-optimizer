import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ProductionPanel } from "../components/production/ProductionPanel";
import type { ContentReadinessSnapshot } from "../lib/state/contentReadiness";

const pageSource = readFileSync("app/page.tsx", "utf8");
const apiClientSource = readFileSync("lib/api/client.ts", "utf8");

const readyContent: ContentReadinessSnapshot = {
  status: "ready_for_publish_check",
  label: "Ready for publish check",
  summary: "2 publishable artifact(s) have source, claim, feedback, and review proof.",
  metrics: {
    publishableArtifactCount: 2,
    sourceBackedArtifactCount: 2,
    claimLinkedArtifactCount: 2,
    acceptedContextEvidenceCount: 4,
    unsupportedClaimCount: 0,
    needsReviewClaimCount: 0,
    openFeedbackCount: 0,
    missingReviewerDecisionCount: 0
  },
  checks: [],
  blockers: [],
  nextActions: ["Run final publish readiness or continue with growth packaging."]
};

test("ProductionPanel renders content readiness preflight metrics", () => {
  const html = renderToStaticMarkup(
    React.createElement(ProductionPanel, {
      disabled: false,
      selectedCount: 0,
      contentReadiness: readyContent,
      onBuildMedia: async () => undefined,
      onBuildDistribution: async () => undefined,
      onCheckReadiness: async () => undefined
    })
  );

  assert.match(html, /Content readiness/);
  assert.match(html, /Growth package/);
  assert.match(html, /Ready for publish check/);
  assert.match(html, /2 content/);
  assert.match(html, /2 source-backed/);
  assert.match(html, /4 accepted sources/);
  assert.match(html, /Run final publish readiness/);
  assert.doesNotMatch(html, /disabled=""/);
});

test("ProductionPanel disables production actions when no content is available", () => {
  const noContent: ContentReadinessSnapshot = {
    ...readyContent,
    status: "no_content",
    label: "No content",
    summary: "Generate source-backed post, reel, and Substack drafts.",
    metrics: {
      ...readyContent.metrics,
      publishableArtifactCount: 0,
      sourceBackedArtifactCount: 0,
      claimLinkedArtifactCount: 0,
      acceptedContextEvidenceCount: 0
    },
    blockers: ["0 publishable artifact(s) found."],
    nextActions: ["Generate source-backed post, reel, and Substack drafts."]
  };
  const html = renderToStaticMarkup(
    React.createElement(ProductionPanel, {
      disabled: false,
      selectedCount: 0,
      contentReadiness: noContent,
      onBuildMedia: async () => undefined,
      onBuildDistribution: async () => undefined,
      onCheckReadiness: async () => undefined
    })
  );

  assert.match(html, /No content/);
  assert.match(html, /Generate source-backed post, reel, and Substack drafts/);
  assert.equal((html.match(/disabled=""/g) ?? []).length, 3);
});

test("ProductionPanel blocks packaging but keeps publish check available for blocked content", () => {
  const blockedContent: ContentReadinessSnapshot = {
    ...readyContent,
    status: "blocked",
    label: "Blocked",
    summary: "Run web research and source-ledger repair before packaging.",
    metrics: {
      ...readyContent.metrics,
      sourceBackedArtifactCount: 1,
      unsupportedClaimCount: 1
    },
    blockers: ["1 publishable artifact(s) lack source evidence."],
    nextActions: ["Run web research and source-ledger repair before packaging."]
  };
  const html = renderToStaticMarkup(
    React.createElement(ProductionPanel, {
      disabled: false,
      selectedCount: 0,
      contentReadiness: blockedContent,
      onBuildMedia: async () => undefined,
      onBuildDistribution: async () => undefined,
      onCheckReadiness: async () => undefined
    })
  );

  assert.match(html, /Blocked/);
  assert.match(html, /1 publishable artifact\(s\) lack source evidence/);
  assert.equal((html.match(/disabled=""/g) ?? []).length, 2);
  assert.match(html, />Publish check</);
});

test("ProductionPanel renders publish channel smoke evidence", () => {
  const html = renderToStaticMarkup(
    React.createElement(ProductionPanel, {
      disabled: false,
      selectedCount: 1,
      contentReadiness: readyContent,
      productionStatus: {
        label: "Publish readiness",
        summary: "Publishing readiness is blocked by channel credentials.",
        readinessStatus: "blocked",
        blockingIssues: ["missing_publish_channel_credentials"],
        nextActions: ["Configure publishing-channel credentials before live publication."],
        publishChannelChecks: [
          {
            platform: "instagram_post",
            credential_envs: ["INSTAGRAM_ACCESS_TOKEN"],
            credential_status: "configured",
            policy_status: "acknowledged",
            blocking_issues: [],
            recommended_next_actions: []
          },
          {
            platform: "linkedin",
            credential_envs: ["LINKEDIN_ACCESS_TOKEN"],
            credential_status: "configured",
            policy_status: "acknowledged",
            blocking_issues: [],
            recommended_next_actions: []
          },
          {
            platform: "instagram_reel",
            credential_envs: ["INSTAGRAM_ACCESS_TOKEN"],
            credential_status: "configured",
            policy_status: "acknowledged",
            blocking_issues: [],
            recommended_next_actions: []
          },
          {
            platform: "x_thread",
            credential_envs: ["X_ACCESS_TOKEN", "X_API_KEY"],
            credential_status: "missing",
            policy_status: "needs_review",
            blocking_issues: ["missing_publish_channel_credentials"],
            recommended_next_actions: [
              "Configure one of X_ACCESS_TOKEN, X_API_KEY before publishing to x_thread."
            ]
          },
          {
            platform: "substack",
            credential_envs: ["SUBSTACK_API_TOKEN"],
            credential_status: "missing",
            policy_status: "needs_review",
            blocking_issues: ["missing_publish_channel_credentials"],
            recommended_next_actions: [
              "Configure one of SUBSTACK_API_TOKEN before publishing to substack."
            ]
          }
        ]
      },
      onBuildMedia: async () => undefined,
      onBuildDistribution: async () => undefined,
      onCheckReadiness: async () => undefined
    })
  );

  assert.match(html, /Publish channel checks/);
  assert.match(html, /instagram post: credentials configured \(INSTAGRAM_ACCESS_TOKEN\), policy acknowledged/);
  assert.match(html, /x thread: credentials missing \(X_ACCESS_TOKEN or X_API_KEY\), policy needs review/);
  assert.match(html, /Configure one of X_ACCESS_TOKEN, X_API_KEY before publishing to x_thread/);
  assert.match(html, /substack: credentials missing \(SUBSTACK_API_TOKEN\), policy needs review/);
  assert.match(html, /Configure one of SUBSTACK_API_TOKEN before publishing to substack/);
  assert.match(html, /missing publish channel credentials/);
});

test("production actions use a synchronous single-flight gate before async work", () => {
  assert.match(pageSource, /const productionActionGateRef = useRef\(\{ inFlight: false, token: 0 \}\);/);
  for (const handlerName of [
    "handleBuildGrowthPackage",
    "handleBuildMediaPlan",
    "handleCheckPublishReadiness"
  ]) {
    const handlerIndex = pageSource.indexOf(`async function ${handlerName}()`);
    const nextHandlerIndex = pageSource.indexOf("async function ", handlerIndex + 1);
    const handlerSource = pageSource.slice(
      handlerIndex,
      nextHandlerIndex === -1 ? undefined : nextHandlerIndex
    );

    assert.notEqual(handlerIndex, -1);
    assert.match(handlerSource, /beginRunAction\(productionActionGateRef\.current\)/);
    assert.match(handlerSource, /isRunVersionedActionCurrent\(/);
    assert.match(handlerSource, /finishRunAction\(productionActionGateRef\.current, productionToken\)/);
  }
  assert.match(pageSource, /invalidateRunAction\(productionActionGateRef\.current\)/);
  assert.match(apiClientSource, /check_publish_channel_readiness: true/);
  assert.match(apiClientSource, /acknowledge_publish_channel_policy: false/);
});
