import React, { useState, useEffect, useRef } from 'react';
import { projectsAPI } from '../api';

const GraphVisualization = ({ projectId }) => {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const canvasRef = useRef(null);

  useEffect(() => {
    loadGraphData();
  }, [projectId]);

  useEffect(() => {
    if (graphData && canvasRef.current) {
      drawGraph();
    }
  }, [graphData]);

  const loadGraphData = async () => {
    try {
      const response = await projectsAPI.getGraph(projectId, 100);
      setGraphData(response.data);
    } catch (err) {
      setError('Failed to load graph data');
    } finally {
      setLoading(false);
    }
  };

  const drawGraph = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = '#f9fafb';
    ctx.fillRect(0, 0, width, height);

    if (!graphData || graphData.nodes.length === 0) {
      ctx.fillStyle = '#6b7280';
      ctx.font = '16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No data to visualize', width / 2, height / 2);
      return;
    }

    // Create force-directed layout positions
    const nodes = graphData.nodes.map((node, index) => ({
      ...node,
      x: Math.random() * (width - 100) + 50,
      y: Math.random() * (height - 100) + 50,
      vx: 0,
      vy: 0,
    }));

    // Simple force simulation
    for (let iteration = 0; iteration < 100; iteration++) {
      // Repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 1000 / (distance * distance);

          nodes[i].vx -= (dx / distance) * force;
          nodes[i].vy -= (dy / distance) * force;
          nodes[j].vx += (dx / distance) * force;
          nodes[j].vy += (dy / distance) * force;
        }
      }

      // Attraction along edges
      graphData.edges.forEach(edge => {
        const source = nodes.find(n => n.id === edge.source);
        const target = nodes.find(n => n.id === edge.target);
        if (source && target) {
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = distance * 0.01;

          source.vx += (dx / distance) * force;
          source.vy += (dy / distance) * force;
          target.vx -= (dx / distance) * force;
          target.vy -= (dy / distance) * force;
        }
      });

      // Apply velocity
      nodes.forEach(node => {
        node.x += node.vx * 0.1;
        node.y += node.vy * 0.1;
        node.vx *= 0.8;
        node.vy *= 0.8;

        // Keep nodes within bounds
        node.x = Math.max(50, Math.min(width - 50, node.x));
        node.y = Math.max(50, Math.min(height - 50, node.y));
      });
    }

    // Draw edges
    ctx.strokeStyle = '#9ca3af';
    ctx.lineWidth = 1;
    graphData.edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source);
      const target = nodes.find(n => n.id === edge.target);
      if (source && target) {
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();

        // Draw edge label
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        ctx.fillStyle = '#6b7280';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(edge.label, midX, midY);
      }
    });

    // Draw nodes
    nodes.forEach(node => {
      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, 20, 0, 2 * Math.PI);
      ctx.fillStyle = '#4f46e5';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Node label
      ctx.fillStyle = '#1f2937';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      const label = node.label.length > 20 ? node.label.substring(0, 17) + '...' : node.label;
      ctx.fillText(label, node.x, node.y + 35);
    });
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <div className="text-lg">Loading graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No graph data</h3>
        <p className="mt-1 text-sm text-gray-500">
          Upload and process documents to build your knowledge graph.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Knowledge Graph Visualization</h3>
          <p className="text-sm text-gray-600">
            {graphData.statistics.nodes} entities, {graphData.statistics.relationships} relationships
          </p>
        </div>
        <button
          onClick={loadGraphData}
          className="px-4 py-2 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100"
        >
          🔄 Refresh
        </button>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <canvas
          ref={canvasRef}
          width={1000}
          height={600}
          className="w-full"
          style={{ maxWidth: '100%', height: 'auto' }}
        />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4 text-center">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-2xl font-bold text-indigo-600">{graphData.nodes.length}</div>
          <div className="text-sm text-gray-600">Visible Entities</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-2xl font-bold text-indigo-600">{graphData.edges.length}</div>
          <div className="text-sm text-gray-600">Visible Relationships</div>
        </div>
<div className="bg-gray-50 rounded-lg p-4">
  <div className="text-2xl font-bold text-indigo-600">{graphData.statistics.documents}</div>
  <div className="text-sm text-gray-600">Source Documents</div>
</div>
      </div>
    </div>
  );
};

export default GraphVisualization;
