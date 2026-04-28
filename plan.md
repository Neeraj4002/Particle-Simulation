# Project Plan: Swarm Intelligence Morphogenesis Simulator

## Objective
To build a simulation where thousands of autonomous particles (nanobots) inherently "know" how to self-assemble into complex 3D structures (based on a text prompt) using distributed Neural Cellular Automata (NCA) and Graph Neural Networks (GNN), replicating biological growth and "programmable matter."

## Tech Stack
*   **Frontend:** HTML5, CSS3, JavaScript, WebGL / WebGPU (via Three.js for rendering millions of particles efficiently).
*   **Backend:** Python, FastAPI.
*   **AI / Compute:** PyTorch or TensorFlow for training the NCA model; Compute Shaders for running the distributed neural nets on the GPU in real-time.

---

## Phase 1: Environment & Engine Foundation
**Goal:** Create the basic physics and rendering engine capable of handling localized particle interactions.
*   [ ] Set up a Three.js scene with WebGL/WebGPU compute shaders to handle 10,000+ particles.
*   [ ] Implement a spatial hashing grid or BVH (Bounding Volume Hierarchy) so particles can quickly find their immediate neighbors without global calculations.
*   [ ] Implement baseline Boids physics (cohesion, alignment, separation) to act as the base movement behavior before neural logic takes over.

## Phase 2: The "DNA" Prompt System
**Goal:** Convert text prompts into mathematical "seeds" that particles can understand.
*   [ ] Integrate a text-to-feature model (like CLIP).
*   [ ] When the user types "apple", push the prompt through the model to retrieve a mathematical embedding (the "DNA").
*   [ ] Broadcast this static DNA vector to the memory state of every individual particle.

## Phase 3: Neural Cellular Automata (NCA) Design
**Goal:** Give every particle a microscopic brain that relies *only* on local data.
*   [ ] Design the NCA architecture: A tiny neural network that takes in:
    1.  The DNA vector.
    2.  The current state of the particle (e.g., color, density, locked/moving).
    3.  The states of particles within a tight radius.
*   [ ] The output of this NCA dictates the particle's next velocity vector and color mapping.
*   [ ] Build the Python training loop: Train the NCA in PyTorch by penalizing the swarm if it doesn't match voxelized 3D models (starting with simple shapes like a sphere, then moving to complex ones).

## Phase 4: Training & Emergence (Morphogenesis)
**Goal:** Train the particles to grow and assemble organically.
*   [ ] Start with a single "Seed" particle in the simulation.
*   [ ] Program a division rule: Given the DNA prompt, the seed particle duplicates itself.
*   [ ] Apply the pre-trained NCA weights to the compute shader. Watch the cells divide, push each other outward, and differentiate (e.g., surface particles turn red, stem particles turn green) to form the "apple."

## Phase 5: Self-Healing and Disturbance
**Goal:** Prove the swarm is stateless and intelligent.
*   [ ] Add user interaction hooks (mouse click/drag to delete or scatter particles).
*   [ ] Ensure the local NCA rules naturally trigger a "healing" response, where remaining particles sense the void and divide/move to reconstruct the damaged area—demonstrating true programmable matter.

## Phase 6: Refinement & Scaling
*   [ ] Optimize GPU Compute Shaders to handle 100,000+ particles at 60FPS.
*   [ ] Refine the interpolation between the text embedding and the final 3D shape generation.
*   [ ] Add lighting, material properties (e.g., metallic for Iron Man nanotech), and bloom effects.
