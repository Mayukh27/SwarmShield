import { create } from "zustand";

/**
 * Central state for the active scan: its status, the running log feed,
 * and the attack-log lineage that feeds the graph. Kept flat and simple
 * on purpose — this is a single-scan-at-a-time demo dashboard.
 */
export const useScanStore = create((set, get) => ({
  targets: [],
  selectedTargetId: null,

  activeScan: null, // ScanOut
  attackLogs: [], // AttackLogOut[] — mutation lineage
  vulnerabilities: [],
  events: [], // AgentLogEvent[] — raw live feed for the console
  memory: [], // MemoryRecord[] — shared cross-agent memory for this scan
  attackDna: [], // AttackDNARecord[] — mutation lineage per vector

  setTargets: (targets) => set({ targets }),
  selectTarget: (id) => set({ selectedTargetId: id }),

  startNewScan: (scan) =>
    set({
      activeScan: scan,
      attackLogs: [],
      vulnerabilities: [],
      events: [],
      memory: [],
      attackDna: [],
    }),

  updateScanStatus: (patch) =>
    set((state) => ({ activeScan: { ...state.activeScan, ...patch } })),

  pushEvent: (event) =>
    set((state) => ({ events: [...state.events, event].slice(-500) })),

  setAttackLogs: (attackLogs) => set({ attackLogs }),
  addAttackLog: (log) =>
    set((state) => ({ attackLogs: [...state.attackLogs, log] })),

  setVulnerabilities: (vulnerabilities) => set({ vulnerabilities }),
  addVulnerability: (vuln) =>
    set((state) => ({ vulnerabilities: [...state.vulnerabilities, vuln] })),

  setMemory: (memory) => set({ memory }),
  setAttackDna: (attackDna) => set({ attackDna }),
}));
