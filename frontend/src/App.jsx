import { useState } from 'react'
import SearchPage from './components/SearchPage'
import IngestPage from './components/IngestPage'
import SettingsPage from './components/SettingsPage'

function App() {
  const [currentPage, setCurrentPage] = useState('search')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                Semantic Search Service
              </h1>
            </div>
            <div className="flex space-x-8">
              <button
                onClick={() => setCurrentPage('search')}
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  currentPage === 'search'
                    ? 'border-blue-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Search
              </button>
              <button
                onClick={() => setCurrentPage('ingest')}
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  currentPage === 'ingest'
                    ? 'border-blue-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Ingest
              </button>
              <button
                onClick={() => setCurrentPage('settings')}
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  currentPage === 'settings'
                    ? 'border-blue-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Settings
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {currentPage === 'search' ? <SearchPage /> :
         currentPage === 'ingest' ? <IngestPage /> :
         <SettingsPage />}
      </main>
    </div>
  )
}

export default App
