import React, { useEffect, useRef } from 'react';
import * as monaco from 'monaco-editor';
import { installMonacoWorkers } from '../../../shared/monaco/workerEnvironment';

installMonacoWorkers();

interface MonacoEditorProps {
  value: string;
  language?: string;
  onChange?: (val: string) => void;
  readOnly?: boolean;
}

export const MonacoCodeEditor: React.FC<MonacoEditorProps> = ({
  value,
  language = 'python',
  onChange,
  readOnly = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const editor = monaco.editor.create(containerRef.current, {
      value,
      language: language === 'py' ? 'python' : language === 'js' ? 'javascript' : language || 'plaintext',
      theme: 'vs-dark',
      automaticLayout: true,
      readOnly,
      fontSize: 12,
      fontFamily: 'monospace',
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      lineNumbers: 'on',
      folding: true,
      renderLineHighlight: 'all',
      tabSize: 2,
    });

    editorRef.current = editor;

    const disposable = editor.onDidChangeModelContent(() => {
      const currentVal = editor.getValue();
      onChange?.(currentVal);
    });

    return () => {
      disposable.dispose();
      editor.dispose();
      editorRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (editorRef.current && editorRef.current.getValue() !== value) {
      editorRef.current.setValue(value);
    }
  }, [value]);

  useEffect(() => {
    if (editorRef.current) {
      const model = editorRef.current.getModel();
      if (model) {
        const lang = language === 'py' ? 'python' : language === 'js' ? 'javascript' : language || 'plaintext';
        monaco.editor.setModelLanguage(model, lang);
      }
    }
  }, [language]);

  return <div ref={containerRef} className="w-full h-full min-h-[400px] rounded-xl overflow-hidden border border-slate-800" />;
};
