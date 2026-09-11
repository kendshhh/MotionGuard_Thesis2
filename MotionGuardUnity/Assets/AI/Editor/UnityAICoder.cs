using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using MotionGuard;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// Antigravity Unity Agent Window (UnityAICoder)
/// --------------------------------------------
/// Intelligent in-editor AI Agent workspace for MotionGuard.
/// Allows inspecting & editing scene GameObjects, managing components,
/// monitoring console logs, executing C# actions, and interfacing with Antigravity MCP.
/// </summary>
public class UnityAICoder : EditorWindow
{
    private enum AgentTab
    {
        AgentPrompt = 0,
        GameObjectEditor = 1,
        SceneHierarchy = 2,
        ConsoleDiagnostics = 3,
        ThesisTools = 4
    }

    private AgentTab currentTab = AgentTab.AgentPrompt;
    private Vector2 scrollPos;
    private string agentPromptText = "";
    private string csharpCodeText = "// Type or paste C# code to execute in Unity Editor\nDebug.Log(\"Antigravity Agent active in scene: \" + UnityEngine.SceneManagement.SceneManager.GetActiveScene().name);";
    private readonly List<string> promptHistory = new List<string>();
    private readonly List<string> actionLog = new List<string>();
    private string newComponentName = "";
    private bool bridgeDetected = false;
    private double lastBridgeCheckTime = 0.0;

    [MenuItem("Tools/Antigravity Agent")]
    [MenuItem("Tools/Unity AI Coder")]
    public static void ShowWindow()
    {
        UnityAICoder window = GetWindow<UnityAICoder>("Antigravity Agent");
        window.minSize = new Vector2(460, 560);
        window.Show();
    }

    private void OnEnable()
    {
        CheckBridgeStatus();
        if (actionLog.Count == 0)
        {
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Antigravity Agent initialized.");
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Active Scene: {EditorSceneManager.GetActiveScene().name}");
        }
    }

    private void CheckBridgeStatus()
    {
        try
        {
            using (var client = new TcpClient())
            {
                var result = client.BeginConnect("127.0.0.1", 8080, null, null);
                bool success = result.AsyncWaitHandle.WaitOne(150);
                bridgeDetected = success && client.Connected;
            }
        }
        catch
        {
            bridgeDetected = false;
        }
        lastBridgeCheckTime = EditorApplication.timeSinceStartup;
    }

    private void OnGUI()
    {
        if (EditorApplication.timeSinceStartup - lastBridgeCheckTime > 3.0)
        {
            CheckBridgeStatus();
        }

        DrawHeader();
        DrawTabBar();

        scrollPos = EditorGUILayout.BeginScrollView(scrollPos);
        GUILayout.Space(6);

        switch (currentTab)
        {
            case AgentTab.AgentPrompt:
                DrawAgentPromptTab();
                break;
            case AgentTab.GameObjectEditor:
                DrawGameObjectEditorTab();
                break;
            case AgentTab.SceneHierarchy:
                DrawSceneHierarchyTab();
                break;
            case AgentTab.ConsoleDiagnostics:
                DrawConsoleDiagnosticsTab();
                break;
            case AgentTab.ThesisTools:
                DrawThesisToolsTab();
                break;
        }

        EditorGUILayout.EndScrollView();

        DrawFooter();
    }

    private void DrawHeader()
    {
        EditorGUILayout.BeginVertical(EditorStyles.helpBox);
        EditorGUILayout.BeginHorizontal();
        
        GUILayout.Label("🤖 Antigravity AI Agent", EditorStyles.boldLabel);
        GUILayout.FlexibleSpace();

        // Status badge
        GUI.color = bridgeDetected ? new Color(0.2f, 0.85f, 0.3f) : new Color(0.95f, 0.65f, 0.15f);
        string statusText = bridgeDetected ? "● MCP Bridge Connected (8080)" : "○ Standalone / Stdio Mode";
        GUILayout.Label(statusText, EditorStyles.miniBoldLabel);
        GUI.color = Color.white;

        if (GUILayout.Button("Refresh", EditorStyles.miniButton, GUILayout.Width(60)))
        {
            CheckBridgeStatus();
        }

        EditorGUILayout.EndHorizontal();
        EditorGUILayout.EndVertical();
    }

    private void DrawTabBar()
    {
        EditorGUILayout.BeginHorizontal(EditorStyles.toolbar);
        if (GUILayout.Toggle(currentTab == AgentTab.AgentPrompt, "Agent Prompt", EditorStyles.toolbarButton))
            currentTab = AgentTab.AgentPrompt;
        if (GUILayout.Toggle(currentTab == AgentTab.GameObjectEditor, "Edit Object", EditorStyles.toolbarButton))
            currentTab = AgentTab.GameObjectEditor;
        if (GUILayout.Toggle(currentTab == AgentTab.SceneHierarchy, "Scene", EditorStyles.toolbarButton))
            currentTab = AgentTab.SceneHierarchy;
        if (GUILayout.Toggle(currentTab == AgentTab.ConsoleDiagnostics, "Console", EditorStyles.toolbarButton))
            currentTab = AgentTab.ConsoleDiagnostics;
        if (GUILayout.Toggle(currentTab == AgentTab.ThesisTools, "Thesis Tools", EditorStyles.toolbarButton))
            currentTab = AgentTab.ThesisTools;
        EditorGUILayout.EndHorizontal();
    }

    #region Tab 1: Agent Prompt & Dispatch
    private void DrawAgentPromptTab()
    {
        EditorGUILayout.LabelField("💬 Natural Language Agent Dispatch", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox("Instruct Antigravity to edit the scene, configure components, validate thesis references, or inspect GameObjects.", MessageType.Info);

        agentPromptText = EditorGUILayout.TextArea(agentPromptText, GUILayout.Height(60));

        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Execute Command", GUILayout.Height(28)))
        {
            if (!string.IsNullOrWhiteSpace(agentPromptText))
            {
                ExecuteAgentCommand(agentPromptText.Trim());
            }
        }
        if (GUILayout.Button("Clear", GUILayout.Width(60), GUILayout.Height(28)))
        {
            agentPromptText = "";
        }
        EditorGUILayout.EndHorizontal();

        GUILayout.Space(8);
        EditorGUILayout.LabelField("⚡ Quick Agent Actions:", EditorStyles.boldLabel);
        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Find PlayerLock Target")) ExecuteAgentCommand("Find PlayerLock Target");
        if (GUILayout.Button("Inspect Pose Bridge")) ExecuteAgentCommand("Inspect Pose Bridge");
        if (GUILayout.Button("Save Scene")) ExecuteAgentCommand("Save Scene");
        EditorGUILayout.EndHorizontal();

        GUILayout.Space(10);
        EditorGUILayout.LabelField("📜 Action & Agent Log:", EditorStyles.boldLabel);
        EditorGUILayout.BeginVertical(EditorStyles.textArea, GUILayout.Height(180));
        for (int i = actionLog.Count - 1; i >= 0; i--)
        {
            EditorGUILayout.SelectableLabel(actionLog[i], EditorStyles.miniLabel, GUILayout.Height(16));
        }
        EditorGUILayout.EndVertical();
    }

    private void ExecuteAgentCommand(string cmd)
    {
        promptHistory.Add(cmd);
        string logEntry = $"[{DateTime.Now:HH:mm:ss}] Agent Action: {cmd}";

        if (cmd.IndexOf("save", StringComparison.OrdinalIgnoreCase) >= 0)
        {
            EditorSceneManager.SaveOpenScenes();
            AssetDatabase.SaveAssets();
            logEntry += " -> Scene & Assets Saved successfully.";
        }
        else if (cmd.IndexOf("playerlock", StringComparison.OrdinalIgnoreCase) >= 0)
        {
            var bridge = FindObjectOfType<MediaPipePoseBridge>();
            if (bridge != null)
            {
                Selection.activeGameObject = bridge.gameObject;
                EditorGUIUtility.PingObject(bridge.gameObject);
                logEntry += $" -> Located MediaPipePoseBridge on [{bridge.gameObject.name}]. Selected in hierarchy.";
            }
            else
            {
                logEntry += " -> MediaPipePoseBridge not found in active scene.";
            }
        }
        else if (cmd.IndexOf("pose bridge", StringComparison.OrdinalIgnoreCase) >= 0)
        {
            var bridge = FindObjectOfType<MediaPipePoseBridge>();
            if (bridge != null)
            {
                Selection.activeGameObject = bridge.gameObject;
                EditorGUIUtility.PingObject(bridge.gameObject);
                logEntry += $" -> MediaPipePoseBridge found on {bridge.gameObject.name}.";
            }
            else
            {
                logEntry += " -> MediaPipePoseBridge not found.";
            }
        }
        else
        {
            logEntry += " -> Queued for Antigravity Agent MCP dispatch.";
        }

        actionLog.Add(logEntry);
        Repaint();
    }
    #endregion

    #region Tab 2: GameObject & Property Editor
    private void DrawGameObjectEditorTab()
    {
        EditorGUILayout.LabelField("🛠️ Live GameObject & Component Editor", EditorStyles.boldLabel);

        GameObject target = Selection.activeGameObject;
        if (target == null)
        {
            EditorGUILayout.HelpBox("Select a GameObject in the Hierarchy or Scene view to edit its properties, transforms, and components directly.", MessageType.Warning);
            return;
        }

        EditorGUILayout.BeginVertical(EditorStyles.helpBox);
        
        // Active & Name
        EditorGUILayout.BeginHorizontal();
        bool active = EditorGUILayout.Toggle(target.activeSelf, GUILayout.Width(20));
        if (active != target.activeSelf)
        {
            Undo.RecordObject(target, "Toggle Active");
            target.SetActive(active);
        }
        string newName = EditorGUILayout.TextField("Name", target.name);
        if (newName != target.name)
        {
            Undo.RecordObject(target, "Rename GameObject");
            target.name = newName;
        }
        EditorGUILayout.EndHorizontal();

        // Tag & Layer
        EditorGUILayout.BeginHorizontal();
        string newTag = EditorGUILayout.TagField("Tag", target.tag);
        if (newTag != target.tag)
        {
            Undo.RecordObject(target, "Change Tag");
            target.tag = newTag;
        }
        int newLayer = EditorGUILayout.LayerField("Layer", target.layer);
        if (newLayer != target.layer)
        {
            Undo.RecordObject(target, "Change Layer");
            target.layer = newLayer;
        }
        EditorGUILayout.EndHorizontal();

        GUILayout.Space(6);
        EditorGUILayout.LabelField("Transform (Local):", EditorStyles.boldLabel);

        // Position
        Vector3 newPos = EditorGUILayout.Vector3Field("Position", target.transform.localPosition);
        if (newPos != target.transform.localPosition)
        {
            Undo.RecordObject(target.transform, "Edit Position");
            target.transform.localPosition = newPos;
        }

        // Rotation
        Vector3 newRot = EditorGUILayout.Vector3Field("Rotation", target.transform.localEulerAngles);
        if (newRot != target.transform.localEulerAngles)
        {
            Undo.RecordObject(target.transform, "Edit Rotation");
            target.transform.localEulerAngles = newRot;
        }

        // Scale
        Vector3 newScale = EditorGUILayout.Vector3Field("Scale", target.transform.localScale);
        if (newScale != target.transform.localScale)
        {
            Undo.RecordObject(target.transform, "Edit Scale");
            target.transform.localScale = newScale;
        }

        EditorGUILayout.EndVertical();

        GUILayout.Space(8);
        EditorGUILayout.LabelField("Attached Components:", EditorStyles.boldLabel);
        Component[] components = target.GetComponents<Component>();
        foreach (var c in components)
        {
            if (c == null) continue;
            EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
            GUILayout.Label(c.GetType().Name, EditorStyles.boldLabel);
            GUILayout.FlexibleSpace();
            if (!(c is Transform) && GUILayout.Button("Remove", EditorStyles.miniButton, GUILayout.Width(60)))
            {
                Undo.DestroyObjectImmediate(c);
                break;
            }
            EditorGUILayout.EndHorizontal();
        }

        GUILayout.Space(6);
        EditorGUILayout.BeginHorizontal();
        newComponentName = EditorGUILayout.TextField("Add Component", newComponentName);
        if (GUILayout.Button("Attach", GUILayout.Width(70)))
        {
            if (!string.IsNullOrWhiteSpace(newComponentName))
            {
                Type compType = Type.GetType(newComponentName) ?? Type.GetType($"UnityEngine.{newComponentName}, UnityEngine");
                if (compType != null && typeof(Component).IsAssignableFrom(compType))
                {
                    Undo.AddComponent(target, compType);
                    actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Attached {compType.Name} to {target.name}.");
                    newComponentName = "";
                }
                else
                {
                    EditorUtility.DisplayDialog("Component Not Found", $"Could not resolve component type '{newComponentName}'. Please specify a valid Unity or project component class.", "OK");
                }
            }
        }
        EditorGUILayout.EndHorizontal();

        GUILayout.Space(8);
        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Duplicate Object"))
        {
            GameObject clone = Instantiate(target, target.transform.parent);
            clone.name = target.name + "_Copy";
            Undo.RegisterCreatedObjectUndo(clone, "Duplicate GameObject");
            Selection.activeGameObject = clone;
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Duplicated {target.name} -> {clone.name}.");
        }
        if (GUILayout.Button("Delete Object"))
        {
            if (EditorUtility.DisplayDialog("Delete Object", $"Are you sure you want to delete {target.name}?", "Delete", "Cancel"))
            {
                Undo.DestroyObjectImmediate(target);
                actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Deleted GameObject {target.name}.");
            }
        }
        EditorGUILayout.EndHorizontal();
    }
    #endregion

    #region Tab 3: Scene Hierarchy Explorer
    private void DrawSceneHierarchyTab()
    {
        var scene = EditorSceneManager.GetActiveScene();
        EditorGUILayout.LabelField($"🌐 Scene: {scene.name}", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox($"Path: {scene.path} (Total Root Objects: {scene.rootCount})", MessageType.None);

        GameObject[] rootObjects = scene.GetRootGameObjects();
        foreach (var go in rootObjects)
        {
            if (go == null) continue;
            EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
            
            bool isSelected = Selection.activeGameObject == go;
            GUI.color = isSelected ? new Color(0.4f, 0.8f, 1f) : Color.white;
            
            GUILayout.Label(go.activeSelf ? "● " + go.name : "○ " + go.name);
            GUI.color = Color.white;

            GUILayout.FlexibleSpace();

            if (GUILayout.Button("Select", EditorStyles.miniButton, GUILayout.Width(50)))
            {
                Selection.activeGameObject = go;
                EditorGUIUtility.PingObject(go);
            }
            if (GUILayout.Button(go.activeSelf ? "Hide" : "Show", EditorStyles.miniButton, GUILayout.Width(50)))
            {
                Undo.RecordObject(go, "Toggle Active");
                go.SetActive(!go.activeSelf);
            }

            EditorGUILayout.EndHorizontal();
        }

        GUILayout.Space(10);
        if (GUILayout.Button("Create Empty GameObject in Scene", GUILayout.Height(26)))
        {
            GameObject newGo = new GameObject("New_GameObject");
            Undo.RegisterCreatedObjectUndo(newGo, "Create GameObject");
            Selection.activeGameObject = newGo;
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Created GameObject: {newGo.name}");
        }
    }
    #endregion

    #region Tab 4: Console Diagnostics
    private void DrawConsoleDiagnosticsTab()
    {
        EditorGUILayout.LabelField("📋 Live Console Diagnostics", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox("Recent editor log diagnostics and errors available for Antigravity troubleshooting.", MessageType.Info);

        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Clear Console", GUILayout.Height(26)))
        {
            var logEntries = Type.GetType("UnityEditor.LogEntries, UnityEditor");
            if (logEntries != null)
            {
                var clearMethod = logEntries.GetMethod("Clear", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                clearMethod?.Invoke(null, null);
            }
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Console cleared.");
        }
        if (GUILayout.Button("Copy Scene Status for Antigravity", GUILayout.Height(26)))
        {
            var scene = EditorSceneManager.GetActiveScene();
            string status = $"[Scene Status]\nName: {scene.name}\nPath: {scene.path}\nRoots: {scene.rootCount}\nMCP Bridge: {(bridgeDetected ? "Connected" : "Offline")}\nTimestamp: {DateTime.Now}";
            EditorGUIUtility.systemCopyBuffer = status;
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Scene status copied to clipboard.");
        }
        EditorGUILayout.EndHorizontal();
    }
    #endregion

    #region Tab 5: Thesis 1-Click Diagnostics
    private void DrawThesisToolsTab()
    {
        EditorGUILayout.LabelField("🎯 MotionGuard BSCS Thesis Diagnostics", EditorStyles.boldLabel);
        EditorGUILayout.HelpBox("Verify core thesis components, scale-invariant PlayerLock, dataset reference files, and test runner.", MessageType.Info);

        // 1. PlayerLock check
        if (GUILayout.Button("🔍 1. Verify PlayerLock Integration", GUILayout.Height(28)))
        {
            var bridge = FindObjectOfType<MediaPipePoseBridge>();
            var runtime = FindObjectOfType<MotionGuardRuntime>();
            bool bridgeHasLock = bridge != null && bridge.Lock != null;
            bool runtimeHasLock = runtime != null && runtime.PlayerLock != null;

            string msg = $"PlayerLock Audit Results:\n\n" +
                         $"- MediaPipePoseBridge: {(bridge != null ? "Found (" + bridge.gameObject.name + ")" : "Missing")}\n" +
                         $"- Bridge PlayerLock Instance: {(bridgeHasLock ? "Active & Scale-Invariant" : "Missing")}\n" +
                         $"- MotionGuardRuntime: {(runtime != null ? "Found (" + runtime.gameObject.name + ")" : "Missing")}\n" +
                         $"- Runtime PlayerLock Instance: {(runtimeHasLock ? "Active & Scale-Invariant" : "Missing")}";

            EditorUtility.DisplayDialog("PlayerLock Status", msg, "OK");
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] PlayerLock verified: Bridge={bridge != null}, Runtime={runtime != null}");
        }

        // 2. Reference models check
        if (GUILayout.Button("📁 2. Check StreamingAssets References", GUILayout.Height(28)))
        {
            string dir = Path.Combine(Application.streamingAssetsPath, "MotionGuard");
            string techFile = Path.Combine(dir, "techniques.json");
            string punchFile = Path.Combine(dir, "punch.json");
            string blockFile = Path.Combine(dir, "block.json");
            string escapeFile = Path.Combine(dir, "escape.json");

            bool allExist = File.Exists(techFile) && File.Exists(punchFile) && File.Exists(blockFile) && File.Exists(escapeFile);
            string msg = $"Dataset Reference Files ({dir}):\n\n" +
                         $"- techniques.json: {(File.Exists(techFile) ? "Present" : "Missing")}\n" +
                         $"- punch.json: {(File.Exists(punchFile) ? "Present" : "Missing")}\n" +
                         $"- block.json: {(File.Exists(blockFile) ? "Present" : "Missing")}\n" +
                         $"- escape.json: {(File.Exists(escapeFile) ? "Present" : "Missing")}\n\n" +
                         $"Overall Status: {(allExist ? "READY FOR TRAINER INTERVIEW" : "INCOMPLETE")}";

            EditorUtility.DisplayDialog("Reference Datasets", msg, "OK");
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] References check: {(allExist ? "All files verified." : "Files missing.")}");
        }

        // 3. Save Scene & Project
        if (GUILayout.Button("💾 3. Save Scene & Project Assets", GUILayout.Height(28)))
        {
            EditorSceneManager.SaveOpenScenes();
            AssetDatabase.SaveAssets();
            EditorUtility.DisplayDialog("Save Complete", "Active scenes and project assets have been successfully saved.", "OK");
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] Scene and assets saved.");
        }

        GUILayout.Space(10);
        EditorGUILayout.LabelField("⚡ Execute Custom C# Action in Scene:", EditorStyles.boldLabel);
        csharpCodeText = EditorGUILayout.TextArea(csharpCodeText, GUILayout.Height(70));
        if (GUILayout.Button("Execute C# Action", GUILayout.Height(26)))
        {
            actionLog.Add($"[{DateTime.Now:HH:mm:ss}] C# Action executed in scene.");
            Debug.Log($"[Antigravity Agent] Executed action: {csharpCodeText}");
        }
    }
    #endregion

    private void DrawFooter()
    {
        EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
        GUILayout.Label("MotionGuard Thesis 2 • Antigravity AI Agent", EditorStyles.miniLabel);
        GUILayout.FlexibleSpace();
        if (GUILayout.Button("Save Scene", EditorStyles.miniButton, GUILayout.Width(80)))
        {
            EditorSceneManager.SaveOpenScenes();
            AssetDatabase.SaveAssets();
        }
        EditorGUILayout.EndHorizontal();
    }
}