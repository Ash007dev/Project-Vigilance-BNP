import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import cytoscape, { Core, ElementDefinition } from "cytoscape";

const API = "http://localhost:8000/api";

interface GraphNode {
  data: {
    id: string;
    label?: string;
    type?: string;
  };
}

interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    label?: string;
    type?: string;
  };
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

        const elements: ElementDefinition[] = [
          ...graph.nodes,
          ...graph.edges,
        ];

        if (cyRef.current) {
          cyRef.current.destroy();
        }

        cyRef.current = cytoscape({
          container: containerRef.current,

          elements,

          layout: {
            name: "cose",
            animate: true,
            animationDuration: 600,
            fit: true,
            padding: 50,
          },

          style: [
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
                width: 28,
                height: 28,
                "border-width": 1,
                "border-color": "#64748b",
                "overlay-opacity": 0,
              },
            },

            {
              selector: 'node[type="ACCOUNT"]',
              style: {
                "background-color": "#4f8cff",
                "border-color": "#8bb5ff",
                width: 34,
                height: 34,
              },
            },

            {
              selector: 'node[type="DEVICE"]',
              style: {
                "background-color": "#a78bfa",
                "border-color": "#c4b5fd",
                shape: "round-rectangle",
                width: 32,
                height: 25,
              },
            },

            {
              selector: 'node[type="IP"]',
              style: {
                "background-color": "#35d39a",
                "border-color": "#6ee7b7",
                shape: "diamond",
                width: 30,
                height: 30,
              },
            },

            {
              selector: 'node[type="WALLET"]',
              style: {
                "background-color": "#f5c451",
                "border-color": "#fde68a",
                shape: "hexagon",
                width: 34,
                height: 30,
              },
            },

            {
              selector: 'node[id="' + account + '"]',
              style: {
                "background-color": "#ff667a",
                "border-color": "#ffb0ba",
                width: 46,
                height: 46,
                "font-size": "11px",
                "font-weight": "800",
                "border-width": 3,
                "shadow-blur": 18,
                "shadow-color": "#ff667a",
                "shadow-opacity": 0.45,
              },
            },

            {
              selector: "edge",
              style: {
                width: 1.5,
                "line-color": "#334155",
                "target-arrow-color": "#64748b",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "arrow-scale": 0.7,
                label: "data(label)",
                color: "#718096",
                "font-size": "8px",
                "text-background-color": "#0b111b",
                "text-background-opacity": 0.9,
                "text-background-padding": "3px",
              },
            },

            {
              selector: 'edge[type="TRANSACTION"]',
              style: {
                "line-color": "#4f8cff",
                "target-arrow-color": "#4f8cff",
                width: 2,
              },
            },

            {
              selector: 'edge[type="DEVICE"]',
              style: {
                "line-color": "#a78bfa",
                "target-arrow-color": "#a78bfa",
                "line-style": "dashed",
              },
            },

            {
              selector: 'edge[type="IP"]',
              style: {
                "line-color": "#35d39a",
                "target-arrow-color": "#35d39a",
                "line-style": "dashed",
              },
            },

            {
              selector: "node:selected",
              style: {
                "border-width": 3,
                "border-color": "#ffffff",
              },
            },

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

  const zoomIn = () => {
    if (!cyRef.current) return;

    cyRef.current.zoom({
      level: cyRef.current.zoom() * 1.2,
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

    cyRef.current.fit(undefined, 50);
  };

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