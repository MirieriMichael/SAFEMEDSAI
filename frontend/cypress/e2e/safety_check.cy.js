describe("Safety Check Badge", () => {
  beforeEach(() => {
    // Mock authentication if needed
    cy.window().then((win) => {
      win.localStorage.setItem("authToken", "mock-token");
    });
  });

  it("shows health risk badge when backend returns safety_check", () => {
    // Intercept the scan API call
    cy.intercept("POST", "**/api/drugs/scan-and-check/", {
      statusCode: 200,
      body: {
        found_drug_names: ["Warfarin", "Aspirin"],
        drug_details: [
          {
            id: 855,
            name: "Warfarin",
            druginfo: {
              administration: "Take with food",
              side_effects: "Bleeding, bruising",
              warnings: "May cause stomach ulcers and bleeding disorders"
            },
            safety_check: {
              safety_badge: "Health Risk",
              matched_allergies: [],
              matched_conditions: ["ulcers"],
              explanation: "This drug may not be safe because it matches your conditions (ulcers)."
            }
          },
          {
            id: 74,
            name: "Aspirin",
            druginfo: {
              administration: "Take with water",
              side_effects: "Stomach upset",
              warnings: "Avoid if you have kidney disease"
            },
            safety_check: {
              safety_badge: "Safe",
              matched_allergies: [],
              matched_conditions: [],
              explanation: "No known risks based on your saved health conditions."
            }
          }
        ],
        interactions: [],
        ai_summary: {
          summary: "Test summary"
        }
      }
    }).as("scan");

    cy.visit("/check");
    
    // Wait for the scan to complete (if auto-scan is enabled)
    // Or trigger scan manually
    cy.wait("@scan", { timeout: 10000 });

    // Check that Health Risk badge appears
    cy.contains("Health Risk").should("exist");
    
    // Check that the explanation text appears
    cy.contains("matches your conditions").should("exist");
    
    // Check that Safe badge also appears for the other drug
    cy.contains("Safe").should("exist");
  });

  it("shows matched allergies in safety check", () => {
    cy.intercept("POST", "**/api/drugs/scan-and-check/", {
      statusCode: 200,
      body: {
        found_drug_names: ["Penicillin"],
        drug_details: [
          {
            id: 100,
            name: "Penicillin",
            druginfo: {
              warnings: "Do not take if allergic to penicillin"
            },
            safety_check: {
              safety_badge: "Health Risk",
              matched_allergies: ["Penicillin"],
              matched_conditions: [],
              explanation: "This drug may not be safe because it matches your allergies (Penicillin)."
            }
          }
        ],
        interactions: [],
        ai_summary: { summary: "Test" }
      }
    }).as("scan");

    cy.visit("/check");
    cy.wait("@scan", { timeout: 10000 });

    cy.contains("Health Risk").should("exist");
    cy.contains("matches your allergies").should("exist");
  });

  it("displays safety badge in drug card", () => {
    cy.intercept("POST", "**/api/drugs/scan-and-check/", {
      statusCode: 200,
      body: {
        found_drug_names: ["Test Drug"],
        drug_details: [
          {
            id: 1,
            name: "Test Drug",
            druginfo: {
              warnings: "Test warning"
            },
            safety_check: {
              safety_badge: "Use With Caution",
              matched_allergies: [],
              matched_conditions: ["diabetes"],
              explanation: "This drug may not be safe because it matches your conditions (diabetes)."
            }
          }
        ],
        interactions: [],
        ai_summary: { summary: "Test" }
      }
    }).as("scan");

    cy.visit("/check");
    cy.wait("@scan", { timeout: 10000 });

    // Check that the badge appears in the drug details section
    cy.get(".details-column").within(() => {
      cy.contains("Test Drug").should("exist");
      cy.contains("Use With Caution").should("exist");
    });
  });

  it("handles missing safety_check gracefully", () => {
    cy.intercept("POST", "**/api/drugs/scan-and-check/", {
      statusCode: 200,
      body: {
        found_drug_names: ["Test Drug"],
        drug_details: [
          {
            id: 1,
            name: "Test Drug",
            druginfo: {
              warnings: "Test warning"
            }
            // No safety_check field
          }
        ],
        interactions: [],
        ai_summary: { summary: "Test" }
      }
    }).as("scan");

    cy.visit("/check");
    cy.wait("@scan", { timeout: 10000 });

    // Should still display drug without error
    cy.contains("Test Drug").should("exist");
    // Badge should not appear
    cy.contains("Health Risk").should("not.exist");
  });
});

