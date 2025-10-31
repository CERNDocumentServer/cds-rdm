import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

document.addEventListener("DOMContentLoaded", () => {
  class ThreeScene {
    constructor(config) {
      this.config = config;
      this.container = config.container;

      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.controls = null;
    }

    init() {
      this.initScene();
      this.initCamera();
      this.initRenderer();
      this.initControls();
      this.addEventListeners();
      this.loadModel();
      this.startRendering();
    }

    initScene() {
      this.scene = new THREE.Scene();
    }

    initCamera() {
      const { camera_x, camera_y, camera_z } = this.config;
      const width = window.innerWidth;
      const height = window.innerHeight;

      this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
      this.camera.position.set(camera_x, camera_y, camera_z);
    }

    initRenderer() {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setPixelRatio(window.devicePixelRatio || 1);
      this.renderer.setClearColor(this.config.background, 1);
      this.renderer.setSize(window.innerWidth, window.innerHeight);
      this.container.appendChild(this.renderer.domElement);
    }

    initControls() {
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.zoomSpeed = 0.5;
    }

    addEventListeners() {
      window.addEventListener("resize", () => {
        const width = window.innerWidth;
        const height = window.innerHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
      });
    }

    loadModel() {
      const loader = new GLTFLoader();
      const { fileURI } = this.config;

      const progressBar = document.getElementById("progress");
      const percentText = document.getElementById("percent");

      if (progressBar) progressBar.style.visibility = "visible";

      loader.load(
        fileURI,
        (gltf) => {
          this.scene.add(gltf.scene);
          if (progressBar) progressBar.style.visibility = "hidden";
          if (percentText) percentText.textContent = "";
        },
        (xhr) => {
          if (percentText && xhr.total) {
            const percentComplete = Math.round((xhr.loaded / xhr.total) * 100);
            percentText.textContent = `${percentComplete}`;
            console.debug(`${percentComplete}% loaded`);
          }
        },
        (error) => {
          console.error("An error occurred loading the GLB file:", error);
        }
      );
    }

    startRendering() {
      const renderLoop = () => {
        requestAnimationFrame(renderLoop);
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
      };
      renderLoop();
    }
  }

  // Configuration
  const config = {
    container: document.getElementById("container"),
    background: 0x000000,
    camera_x: 5,
    camera_y: 5,
    camera_z: 10,
    fileURI: document.getElementById("gltf-previewer").getAttribute("data-file-uri"),
  };

  const app = new ThreeScene(config);
  app.init();
});
