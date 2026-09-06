using UnityEditor;
using UnityEngine;

public class UnityAICoder : EditorWindow
{
    [MenuItem("Tools/Unity AI Coder")]
    public static void ShowWindow()
    {
        GetWindow<UnityAICoder>("Unity AI Coder");
    }

    private void OnGUI()
    {
        GUILayout.Label(
            "Unity AI Coder",
            EditorStyles.boldLabel
        );

        GUILayout.Space(10);

        GUILayout.Label(
            "Your AI coding assistant will go here."
        );
    }
}