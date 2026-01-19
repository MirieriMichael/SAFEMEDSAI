// frontend/src/mockData.js
export const mockApiResponse = {
  interactions: [
    {
      drug_a: { name: "Aspirin" },
      drug_b: { name: "Warfarin" },
      description: "Concurrent use of Aspirin and Warfarin may increase the risk of bleeding. Monitor for signs of bleeding.",
      severity: "MAJOR",
    },
  ],
  drug_details: [
    {
      name: "Aspirin",
      druginfo: {
        administration: "Take with a full glass of water. Do not crush or chew if it is an enteric-coated tablet.",
        side_effects: "Common side effects include upset stomach and heartburn.",
        warnings: "Do not use if you have a bleeding disorder such as hemophilia.",
      },
    },
    {
      name: "Warfarin",
      druginfo: {
        administration: "Take at the same time each day. Follow your doctor's instructions carefully.",
        side_effects: "Can cause serious bleeding. Nausea and stomach pain may also occur.",
        warnings: "Avoid activities where you could be easily injured. Many other drugs can affect warfarin.",
      },
    },
  ],
};