import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import cytoscape, { Core, ElementDefinition } from "cytoscape";

const API = "http://localhost:8000/api";

interface GraphNode {
  id: string;
  type?: string;
  label?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship?: string;
  transaction_id?: string;
  amount?: number;
  currency?: string;
  timestamp?: string;
  channel?: string;
}

interface GraphResponse {
  status: string;
  entity: string;
  node_count: number;
  edge_count: number;
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
}

interface RelationshipGraphProps {
  account: string;
}

const RelationshipGraph: React.FC<RelationshipGraphProps> = ({
  account,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const loadGraph = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await axios.get<GraphResponse>(
          `${API}/graph/${encodeURIComponent(account)}`
        );

        if (cancelled || !containerRef.current) {
          return;
        }

        const graph = response.data.graph;

        /*
         * ---------------------------------------------------------
         * 1. PREPARE NODES
         * ---------------------------------------------------------
         */

        const accountNodes = graph.nodes.filter(
          (node) => node.type === "ACCOUNT"
        );

        const deviceNodes = graph.nodes.filter(
          (node) => node.type === "DEVICE"
        );

        const ipNodes = graph.nodes.filter(
          (node) => node.type === "IP"
        );

        const walletNodes = graph.nodes.filter(
          (node) => node.type === "WALLET"
        );

        /*
         * ---------------------------------------------------------
         * 2. MANUAL POSITIONS
         *
         * Investigated account = center
         * Intermediary accounts = surrounding ring
         * Device/IP/Wallet = bottom area
         * ---------------------------------------------------------
         */

        const positions: Record<
          string,
          {
            x: number;
            y: number;
          }
        > = {};

        const CENTER_X = 600;
        const CENTER_Y = 300;

        // Investigated account
        positions[account] = {
          x: CENTER_X,
          y: CENTER_Y,
        };

        // Other accounts
        const otherAccounts = accountNodes.filter(
          (node) => node.id !== account
        );

        const radiusX = 420;
        const radiusY = 210;

        otherAccounts.forEach((node, index) => {
          const total = otherAccounts.length;

          const angle =
            -Math.PI / 2 + (index * 2 * Math.PI) / total;

          positions[node.id] = {
            x: CENTER_X + radiusX * Math.cos(angle),
            y: CENTER_Y + radiusY * Math.sin(angle),
          };
        });

        // Device nodes
        deviceNodes.forEach((node, index) => {
          positions[node.id] = {
            x: CENTER_X - 180 + index * 120,
            y: CENTER_Y + 330,
          };
        });

        // IP nodes
        ipNodes.forEach((node, index) => {
          positions[node.id] = {
            x: CENTER_X + 180 + index * 120,
            y: CENTER_Y + 330,
          };
        });

        // Wallet nodes
        walletNodes.forEach((node, index) => {
          positions[node.id] = {
            x: CENTER_X + index * 140,
            y: CENTER_Y + 420,
          };
        });

        /*
         * ---------------------------------------------------------
         * 3. CREATE CYTOSCAPE ELEMENTS
         * ---------------------------------------------------------
         */

        const elements: ElementDefinition[] = [
          ...graph.nodes.map((node) => ({
            data: {
              id: node.id,
              label:
                node.id === account
                  ? account
                  : node.label || node.id,
              type: node.type,
            },
            position: positions[node.id] || {
              x: CENTER_X,
              y: CENTER_Y,
            },
          })),

          ...graph.edges.map((edge, index) => ({
            data: {
              id: `edge-${index}`,
              source: edge.source,
              target: edge.target,
              relationship: edge.relationship || "",
              transaction_id: edge.transaction_id || "",
              amount: edge.amount || 0,
              currency: edge.currency || "",
            },
          })),
        ];

        /*
         * ---------------------------------------------------------
         * 4. DESTROY OLD GRAPH
         * ---------------------------------------------------------
         */

        if (cyRef.current) {
          cyRef.current.destroy();
        }

        /*
         * ---------------------------------------------------------
         * 5. CREATE GRAPH
         * ---------------------------------------------------------
         */

        cyRef.current = cytoscape({
          container: containerRef.current,

          elements,

          layout: {
            name: "preset",
            fit: true,
            padding: 80,
          },

          style: [
            /*
             * BASE NODE
             */
            {
              selector: "node",
              style: {
                "background-color": "#334155",
                label: "data(label)",
                color: "#e8edf7",
                "font-size": "10px",
                "font-weight": "600",
                "text-valign": "bottom",
                "text-halign": "center",
                "text-margin-y": 8,
                width: 30,
                height: 30,
                "border-width": 2,
                "border-color": "#64748b",
                "text-outline-width": 3,
                "text-outline-color": "#07111f",
              },
            },

            /*
             * ACCOUNT
             */
            {
              selector: 'node[type="ACCOUNT"]',
              style: {
                "background-color": "#4f8cff",
                "border-color": "#8bb5ff",
                width: 38,
                height: 38,
              },
            },

            /*
             * DEVICE
             */
            {
              selector: 'node[type="DEVICE"]',
              style: {
                "background-color": "#a78bfa",
                "border-color": "#c4b5fd",
                shape: "round-rectangle",
                width: 42,
                height: 30,
              },
            },

            /*
             * IP
             */
            {
              selector: 'node[type="IP"]',
              style: {
                "background-color": "#35d39a",
                "border-color": "#6ee7b7",
                shape: "diamond",
                width: 36,
                height: 36,
              },
            },

            /*
             * WALLET
             */
            {
              selector: 'node[type="WALLET"]',
              style: {
                "background-color": "#f5c451",
                "border-color": "#fde68a",
                shape: "hexagon",
                width: 42,
                height: 36,
              },
            },

            /*
             * INVESTIGATED ENTITY
             */
            {
              selector: 'node[id="' + account + '"]',
              style: {
                "background-color": "#ff667a",
                "border-color": "#ffffff",
                width: 58,
                height: 58,
                "font-size": "12px",
                "font-weight": "800",
                "border-width": 3,
              },
            },

            /*
             * BASE EDGE
             */
            {
              selector: "edge",
              style: {
                width: 1.5,
                "line-color": "#475569",
                "target-arrow-color": "#64748b",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "arrow-scale": 0.7,
              },
            },

            /*
             * TRANSACTION
             */
            {
              selector: 'edge[relationship="TRANSACTION"]',
              style: {
                "line-color": "#4f8cff",
                "target-arrow-color": "#4f8cff",
                width: 2.2,
                opacity: 0.75,
              },
            },

            /*
             * DEVICE RELATIONSHIP
             */
            {
              selector: 'edge[relationship="USES_DEVICE"]',
              style: {
                "line-color": "#a78bfa",
                "target-arrow-color": "#a78bfa",
                "line-style": "dashed",
                width: 1.8,
                opacity: 0.65,
              },
            },

            /*
             * IP RELATIONSHIP
             */
            {
              selector: 'edge[relationship="USES_IP"]',
              style: {
                "line-color": "#35d39a",
                "target-arrow-color": "#35d39a",
                "line-style": "dashed",
                width: 1.8,
                opacity: 0.65,
              },
            },

            /*
             * SELECTED NODE
             */
            {
              selector: "node:selected",
              style: {
                "border-width": 4,
                "border-color": "#ffffff",
              },
            },

            /*
             * SELECTED EDGE
             */
            {
              selector: "edge:selected",
              style: {
                width: 4,
                "line-color": "#ffffff",
                "target-arrow-color": "#ffffff",
              },
            },
          ],
        });

        /*
         * ---------------------------------------------------------
         * 6. NODE CLICK
         * ---------------------------------------------------------
         */

        cyRef.current.on("tap", "node", (event) => {
          const node = event.target;

          console.log("Selected graph node:", {
            id: node.id(),
            label: node.data("label"),
            type: node.data("type"),
          });
        });
      } catch (err) {
        console.error("Graph loading failed:", err);

        if (!cancelled) {
          setError("Unable to load relationship graph.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadGraph();

    return () => {
      cancelled = true;

      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [account]);

  /*
   * ---------------------------------------------------------
   * CONTROLS
   * ---------------------------------------------------------
   */

  const zoomIn = () => {
    if (!cyRef.current) return;

    cyRef.current.zoom({
      level: cyRef.current.zoom() * 1.25,
      renderedPosition: {
        x: cyRef.current.width() / 2,
        y: cyRef.current.height() / 2,
      },
    });
  };

  const zoomOut = () => {
    if (!cyRef.current) return;

    cyRef.current.zoom({
      level: cyRef.current.zoom() * 0.8,
      renderedPosition: {
        x: cyRef.current.width() / 2,
        y: cyRef.current.height() / 2,
      },
    });
  };

  const fitGraph = () => {
    if (!cyRef.current) return;

    cyRef.current.fit(undefined, 70);
  };

  /*
   * ---------------------------------------------------------
   * UI
   * ---------------------------------------------------------
   */

  return (
    <div className="relationship-graph">
      <div className="graph-toolbar">
        <div>
          <h3>Relationship Network</h3>

          <p>
            Transaction, device, IP and wallet relationships for{" "}
            <strong>{account}</strong>
          </p>
        </div>

        <div className="graph-controls">
          <button onClick={zoomIn}>+</button>
          <button onClick={zoomOut}>−</button>
          <button onClick={fitGraph}>FIT</button>
        </div>
      </div>

      <div className="graph-legend">
        <span>
          <i className="legend-dot account" />
          Account
        </span>

        <span>
          <i className="legend-dot device" />
          Device
        </span>

        <span>
          <i className="legend-dot ip" />
          IP
        </span>

        <span>
          <i className="legend-dot wallet" />
          Wallet
        </span>

        <span>
          <i className="legend-dot target" />
          Investigated
        </span>
      </div>

      <div className="graph-container">
        {loading && (
          <div className="graph-state">
            <div className="graph-spinner" />
            <span>Building relationship network...</span>
          </div>
        )}

        {error && !loading && (
          <div className="graph-state graph-error">
            {error}
          </div>
        )}

        <div
          ref={containerRef}
          className="cytoscape-container"
          style={{
            visibility: loading || error ? "hidden" : "visible",
          }}
        />
      </div>
    </div>
  );
};

export default RelationshipGraph;