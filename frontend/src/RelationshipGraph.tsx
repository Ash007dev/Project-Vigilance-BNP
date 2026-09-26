import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import cytoscape, { Core, ElementDefinition } from "cytoscape";

const API = "http://localhost:8000/api";

interface GraphNode {
  id: string;
  type: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
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

type SelectedItem =
  | {
      kind: "node";
      id: string;
      type: string;
    }
  | {
      kind: "edge";
      relationship: string;
      source: string;
      target: string;
      transaction_id?: string;
      amount?: number;
      currency?: string;
      timestamp?: string;
      channel?: string;
    }
  | null;

const RelationshipGraph: React.FC<RelationshipGraphProps> = ({
  account,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedItem, setSelectedItem] = useState<SelectedItem>(null);

  useEffect(() => {
    let cancelled = false;

    const loadGraph = async () => {
      try {
        setLoading(true);
        setError("");
        setSelectedItem(null);

        const response = await axios.get<GraphResponse>(
          `${API}/graph/${encodeURIComponent(account)}`
        );

        if (cancelled || !containerRef.current) {
          return;
        }

        const graph = response.data.graph;

        /*
         * ------------------------------------------------------------
         * CREATE GRAPH ELEMENTS
         * ------------------------------------------------------------
         */

        const elements: ElementDefinition[] = [];

        graph.nodes.forEach((node) => {
          elements.push({
            data: {
              id: node.id,
              label: node.id,
              type: node.type,
            },
          });
        });

        graph.edges.forEach((edge, index) => {
          elements.push({
            data: {
              id:
                edge.transaction_id ||
                `${edge.relationship}-${edge.source}-${edge.target}-${index}`,

              source: edge.source,
              target: edge.target,

              relationship: edge.relationship,

              transaction_id: edge.transaction_id,
              amount: edge.amount,
              currency: edge.currency,
              timestamp: edge.timestamp,
              channel: edge.channel,
            },
          });
        });

        /*
         * ------------------------------------------------------------
         * DESTROY PREVIOUS GRAPH
         * ------------------------------------------------------------
         */

        if (cyRef.current) {
          cyRef.current.destroy();
        }

        /*
         * ------------------------------------------------------------
         * CREATE CYTOSCAPE
         * ------------------------------------------------------------
         */

        const cy = cytoscape({
          container: containerRef.current,

          elements,

          /*
           * IMPORTANT:
           *
           * We are NOT using cose / force-directed layout.
           *
           * The positions are created manually below so that the
           * graph keeps the clean structure.
           */
          layout: {
            name: "preset",
            fit: false,
          },

          style: [
            /*
             * --------------------------------------------------------
             * DEFAULT NODE
             * --------------------------------------------------------
             */

            {
              selector: "node",

              style: {
                "background-color": "#4f8cff",

                label: "data(label)",

                color: "#e8edf7",

                "font-size": "9px",

                "font-weight": "600",

                "text-valign": "bottom",

                "text-halign": "center",

                "text-margin-y": 8,

                width: 34,

                height: 34,

                "border-width": 1,

                "border-color": "#8bb5ff",

                "overlay-opacity": 0,
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

                width: 34,

                height: 34,
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

                width: 38,

                height: 28,
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

                width: 34,

                height: 34,
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

                width: 38,

                height: 32,
              },
            },

            /*
             * INVESTIGATED ACCOUNT
             */

            {
              selector: `node[id="${account}"]`,

              style: {
                "background-color": "#ff667a",

                "border-color": "#ffb0ba",

                width: 58,

                height: 58,

                "font-size": "11px",

                "font-weight": "800",

                "border-width": 3,

                "text-margin-y": 12,
              },
            },

            /*
             * --------------------------------------------------------
             * DEFAULT EDGE
             * --------------------------------------------------------
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

                label: "",

                color: "#94a3b8",

                "font-size": "8px",

                "text-background-color": "#0b111b",

                "text-background-opacity": 0.9,

                "text-background-padding": "3px",
              },
            },

            /*
             * TRANSACTIONS
             */

            {
              selector: 'edge[relationship="TRANSACTION"]',

              style: {
                "line-color": "#4f8cff",

                "target-arrow-color": "#4f8cff",

                width: 2,

                "target-arrow-shape": "triangle",

                "curve-style": "bezier",
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

                width: 1.5,

                "target-arrow-shape": "triangle",
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

                width: 1.5,

                "target-arrow-shape": "triangle",
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

                "overlay-opacity": 0.08,

                "overlay-color": "#ffffff",
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

        cyRef.current = cy;

        /*
         * ------------------------------------------------------------
         * FIXED RADIAL POSITIONS
         * ------------------------------------------------------------
         */

        const accountNodes = graph.nodes.filter(
          (node) => node.type === "ACCOUNT" && node.id !== account
        );

        const deviceNodes = graph.nodes.filter(
          (node) => node.type === "DEVICE"
        );

        const ipNodes = graph.nodes.filter((node) => node.type === "IP");

        const walletNodes = graph.nodes.filter(
          (node) => node.type === "WALLET"
        );

        /*
         * Center of graph
         */

        const centerX = 550;
        const centerY = 300;

        /*
         * Investigated account
         */

        cy.getElementById(account).position({
          x: centerX,
          y: centerY,
        });

        /*
         * Connected accounts in a circle
         */

        const radiusX = 360;
        const radiusY = 210;

        accountNodes.forEach((node, index) => {
          const angle =
            (2 * Math.PI * index) / Math.max(accountNodes.length, 1) -
            Math.PI / 2;

          const x = centerX + radiusX * Math.cos(angle);
          const y = centerY + radiusY * Math.sin(angle);

          cy.getElementById(node.id).position({
            x,
            y,
          });
        });

        /*
         * DEVICE
         */

        deviceNodes.forEach((node) => {
          cy.getElementById(node.id).position({
            x: centerX - 170,
            y: centerY + 245,
          });
        });

        /*
         * IP
         */

        ipNodes.forEach((node) => {
          cy.getElementById(node.id).position({
            x: centerX + 170,
            y: centerY + 245,
          });
        });

        /*
         * WALLET
         */

        walletNodes.forEach((node, index) => {
          cy.getElementById(node.id).position({
            x: centerX + (index - (walletNodes.length - 1) / 2) * 130,
            y: centerY + 245,
          });
        });

        /*
         * Fit AFTER positions have been assigned.
         */

        cy.fit(undefined, 70);

        /*
         * ------------------------------------------------------------
         * NODE CLICK
         * ------------------------------------------------------------
         */

        cy.on("tap", "node", (event) => {
          const node = event.target;

          const nodeId = node.id();

          const nodeType = node.data("type");

          setSelectedItem({
            kind: "node",

            id: nodeId,

            type: nodeType,
          });
        });

        /*
         * ------------------------------------------------------------
         * EDGE CLICK
         * ------------------------------------------------------------
         */

        cy.on("tap", "edge", (event) => {
          const edge = event.target;

          setSelectedItem({
            kind: "edge",

            relationship: edge.data("relationship"),

            source: edge.data("source"),

            target: edge.data("target"),

            transaction_id: edge.data("transaction_id"),

            amount: edge.data("amount"),

            currency: edge.data("currency"),

            timestamp: edge.data("timestamp"),

            channel: edge.data("channel"),
          });
        });

        /*
         * ------------------------------------------------------------
         * CLICK EMPTY GRAPH
         * ------------------------------------------------------------
         */

        cy.on("tap", (event) => {
          if (event.target === cy) {
            setSelectedItem(null);

            cy.elements().unselect();
          }
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
   * ------------------------------------------------------------
   * GRAPH CONTROLS
   * ------------------------------------------------------------
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
   * ------------------------------------------------------------
   * FORMAT AMOUNT
   * ------------------------------------------------------------
   */

  const formatAmount = (amount?: number) => {
    if (amount === undefined || amount === null) {
      return "-";
    }

    return Number(amount).toLocaleString(undefined, {
      maximumFractionDigits: 2,
    });
  };

  /*
   * ------------------------------------------------------------
   * FORMAT DATE
   * ------------------------------------------------------------
   */

  const formatDate = (timestamp?: string) => {
    if (!timestamp) {
      return "-";
    }

    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="relationship-graph">

      {/* =========================================================
          HEADER
      ========================================================= */}

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

      {/* =========================================================
          LEGEND
      ========================================================= */}

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

      {/* =========================================================
          GRAPH AREA
      ========================================================= */}

      <div className="graph-container">

        {loading && (
          <div className="graph-state">

            <div className="graph-spinner" />

            <span>
              Building relationship network...
            </span>

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
            visibility:
              loading || error
                ? "hidden"
                : "visible",
          }}
        />

        {/* =======================================================
            INTERACTION PANEL
        ======================================================= */}

        {selectedItem && (

          <div className="graph-details-panel">

            <button
              className="graph-details-close"
              onClick={() => {
                setSelectedItem(null);

                cyRef.current?.elements().unselect();
              }}
            >
              ×
            </button>

            {/* =================================================
                NODE DETAILS
            ================================================= */}

            {selectedItem.kind === "node" && (

              <>
                <div className="graph-details-eyebrow">
                  SELECTED ENTITY
                </div>

                <h3>Entity Details</h3>

                <div className="graph-detail-item">

                  <span>Identifier</span>

                  <strong>
                    {selectedItem.id}
                  </strong>

                </div>

                <div className="graph-detail-item">

                  <span>Type</span>

                  <strong>
                    {selectedItem.type}
                  </strong>

                </div>

                <div className="graph-detail-item">

                  <span>Status</span>

                  <strong>
                    {selectedItem.id === account
                      ? "Investigated Entity"
                      : "Connected Entity"}
                  </strong>

                </div>

              </>
            )}

            {/* =================================================
                EDGE DETAILS
            ================================================= */}

            {selectedItem.kind === "edge" && (

              <>
                <div className="graph-details-eyebrow">
                  SELECTED RELATIONSHIP
                </div>

                <h3>
                  {selectedItem.relationship ===
                  "TRANSACTION"
                    ? "Transaction Details"
                    : "Relationship Details"}
                </h3>

                <div className="graph-detail-item">

                  <span>Relationship</span>

                  <strong>
                    {selectedItem.relationship}
                  </strong>

                </div>

                <div className="graph-detail-item">

                  <span>From</span>

                  <strong>
                    {selectedItem.source}
                  </strong>

                </div>

                <div className="graph-detail-item">

                  <span>To</span>

                  <strong>
                    {selectedItem.target}
                  </strong>

                </div>

                {selectedItem.transaction_id && (

                  <div className="graph-detail-item">

                    <span>Transaction ID</span>

                    <strong>
                      {selectedItem.transaction_id}
                    </strong>

                  </div>

                )}

                {selectedItem.amount !== undefined && (

                  <div className="graph-detail-item">

                    <span>Amount</span>

                    <strong>
                      {formatAmount(
                        selectedItem.amount
                      )}{" "}
                      {selectedItem.currency || ""}
                    </strong>

                  </div>

                )}

                {selectedItem.channel && (

                  <div className="graph-detail-item">

                    <span>Channel</span>

                    <strong>
                      {selectedItem.channel}
                    </strong>

                  </div>

                )}

                {selectedItem.timestamp && (

                  <div className="graph-detail-item">

                    <span>Timestamp</span>

                    <strong>
                      {formatDate(
                        selectedItem.timestamp
                      )}
                    </strong>

                  </div>

                )}

              </>
            )}

          </div>

        )}

      </div>

    </div>
  );
};

export default RelationshipGraph;