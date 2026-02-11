import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsAPI, documentsAPI, queryAPI } from '../api';
import GraphVisualization from './GraphVisualization';

const ProjectView = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat', 'documents', 'graph'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Chat state
  const [messages, setMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const loadProjectData = async () => {
    try {
      const [projectRes, docsRes, statsRes] = await Promise.all([
        projectsAPI.getOne(projectId),
        documentsAPI.getAll(projectId),
        projectsAPI.getStatistics(projectId),
      ]);
      
      setProject(projectRes.data);
      setDocuments(docsRes.data);
      setStatistics(statsRes.data);
    } catch (err) {
      setError('Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      await documentsAPI.upload(projectId, file, setUploadProgress);
      await loadProjectData();
      event.target.value = ''; // Reset file input
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload file');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm('Delete this document?')) return;

    try {
      await documentsAPI.delete(projectId, documentId);
      await loadProjectData();
    } catch (err) {
      setError('Failed to delete document');
    }
  };

  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!currentQuestion.trim() || isAsking) return;

    const userMessage = {
      role: 'user',
      content: currentQuestion,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setCurrentQuestion('');
    setIsAsking(true);

    try {
      const response = await queryAPI.ask({
        question: userMessage.content,
        project_id: projectId,
        use_memory: true,
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError('Failed to get answer');
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your question.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsAsking(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading project...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="text-gray-600 hover:text-gray-900"
              >
                ← Back
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{project?.name}</h1>
                <p className="text-sm text-gray-600">{project?.description}</p>
              </div>
            </div>
            {statistics && (
              <div className="flex gap-6 text-sm">
                <div className="text-center">
                  <div className="font-bold text-lg">{statistics.documents}</div>
                  <div className="text-gray-600">Documents</div>
                </div>
                <div className="text-center">
                  <div className="font-bold text-lg">{statistics.nodes}</div>
                  <div className="text-gray-600">Entities</div>
                </div>
                <div className="text-center">
                  <div className="font-bold text-lg">{statistics.relationships}</div>
                  <div className="text-gray-600">Relations</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-8">
            <button
              onClick={() => setActiveTab('chat')}
              className={`py-4 px-2 border-b-2 font-medium ${
                activeTab === 'chat'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`py-4 px-2 border-b-2 font-medium ${
                activeTab === 'documents'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Documents
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={`py-4 px-2 border-b-2 font-medium ${
                activeTab === 'graph'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Knowledge Graph
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="bg-white rounded-lg shadow h-[calc(100vh-300px)] flex flex-col">
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 mt-12">
                  <p className="text-lg mb-2">Ask a question about your documents</p>
                  <p className="text-sm">Upload documents first to build your knowledge base</p>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-2xl rounded-lg px-4 py-3 ${
                        msg.role === 'user'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-300 text-sm">
                          <span className="font-semibold">Sources: </span>
                          {msg.sources.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isAsking && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-4 py-3">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="border-t p-4">
              <form onSubmit={handleAskQuestion} className="flex gap-2">
                <input
                  type="text"
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  placeholder="Ask a question..."
                  disabled={isAsking || documents.length === 0}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
                />
                <button
                  type="submit"
                  disabled={isAsking || !currentQuestion.trim() || documents.length === 0}
                  className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:bg-gray-400"
                >
                  Send
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div>
            <div className="mb-6">
              <label className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 cursor-pointer inline-block">
                {uploading ? `Uploading... ${uploadProgress}%` : 'Upload Document'}
                <input
                  type="file"
                  onChange={handleFileUpload}
                  accept=".pdf,.docx,.doc,.txt"
                  disabled={uploading}
                  className="hidden"
                />
              </label>
              <p className="text-sm text-gray-600 mt-2">
                Supports PDF, DOCX, and TXT files
              </p>
            </div>

            {documents.length === 0 ? (
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
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No documents</h3>
                <p className="mt-1 text-sm text-gray-500">Upload documents to start building your knowledge base.</p>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Filename
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Size
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Uploaded
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {documents.map((doc) => (
                      <tr key={doc.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {doc.filename}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
                              doc.processed
                                ? 'bg-green-100 text-green-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {doc.processed ? 'Processed' : 'Processing'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(doc.uploaded_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                          <button
                            onClick={() => handleDeleteDocument(doc.id)}
                            className="text-red-600 hover:text-red-900"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Graph Tab */}
        {activeTab === 'graph' && (
          <div>
            <GraphVisualization projectId={projectId} />
          </div>
        )}
      </main>
    </div>
  );
};

export default ProjectView;
