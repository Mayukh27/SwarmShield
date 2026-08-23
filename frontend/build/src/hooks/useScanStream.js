import { useEffect, useRef } from "react";
import { scanStreamUrl } from "../lib/api";
import { useScanStore } from "../store/scanStore";
import { refreshScanData } from "../lib/refreshScan";

/**
 * Subscribes to /scans/{id}/stream via SSE while `scanId` is set.
 * Pushes every event into the store's live feed, and additionally
 * re-fetches attack logs / vulnerabilities / scan status on the events
 * that mean "something new landed in the DB" — keeping the graph and
 * scorecard in sync without needing to duplicate full row payloads over
 * the wire.
 */
export function useScanStream(scanId) {
  const pushEvent = useScanStore((s) => s.pushEvent);
  const sourceRef = useRef(null);

  useEffect(() => {
    if (!scanId) return;

    const es = new EventSource(scanStreamUrl(scanId));
    sourceRef.current = es;

    const refreshLogsAndVulns = async () => {
      try {
        await refreshScanData(scanId);
      } catch {
        // best-effort refresh; the SSE stream is still the source of truth for the console
      }
    };

    const handle = (eventType) => (e) => {
      const data = JSON.parse(e.data);
      pushEvent({ ...data, event_type: eventType });
      if (
        ["agent_action", "sentinel_verdict", "vulnerability_found", "scan_status", "memory_consulted", "dna_mutation"].includes(
          eventType
        )
      ) {
        refreshLogsAndVulns();
      }
    };

    es.addEventListener("agent_action", handle("agent_action"));
    es.addEventListener("sentinel_verdict", handle("sentinel_verdict"));
    es.addEventListener("vulnerability_found", handle("vulnerability_found"));
    es.addEventListener("scan_status", handle("scan_status"));
    es.addEventListener("memory_consulted", handle("memory_consulted"));
    es.addEventListener("dna_mutation", handle("dna_mutation"));
    es.onerror = () => {
      // Stream closes naturally when the backend finishes emitting scan_status=completed/failed
      es.close();
    };

    return () => es.close();
  }, [scanId, pushEvent]);
}
