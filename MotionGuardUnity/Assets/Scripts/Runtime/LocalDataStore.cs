using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace MotionGuard {
    public sealed class LocalDataStore {
        readonly string root;
        public LocalDataStore(string rootPath=null) { root=rootPath??Application.persistentDataPath; Directory.CreateDirectory(root); }
        public T ReadStreaming<T>(string relativePath) where T:new() { var path=Path.Combine(Application.streamingAssetsPath,relativePath); return File.Exists(path)?JsonUtility.FromJson<T>(File.ReadAllText(path)):new T(); }
        public T Load<T>(string file) where T:new() { var path=Path.Combine(root,file); return File.Exists(path)?JsonUtility.FromJson<T>(File.ReadAllText(path)):new T(); }
        public void Save<T>(string file,T value) { File.WriteAllText(Path.Combine(root,file),JsonUtility.ToJson(value,true)); }
    }
}
