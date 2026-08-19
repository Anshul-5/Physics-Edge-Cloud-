import torch
import torch.nn as nn
import torch.nn.functional as F

class MemoryModule(nn.Module):
    def __init__(self, mem_dim, fea_dim, shrink_thres=0.0025):
        """
        Memory Module for the Autoencoder.
        Stores `mem_dim` prototype embeddings of size `fea_dim`.
        """
        super(MemoryModule, self).__init__()
        self.mem_dim = mem_dim
        self.fea_dim = fea_dim
        self.weight = nn.Parameter(torch.Tensor(self.mem_dim, self.fea_dim))
        self.shrink_thres = shrink_thres
        self.reset_parameters()

    def reset_parameters(self):
        import math
        stdv = 1. / math.sqrt(self.weight.size(1))
        self.weight.data.uniform_(-stdv, stdv)

    def forward(self, x):
        """
        x: (batch_size, fea_dim)
        Returns:
            z_hat: Reconstructed embedding using memory prototypes
            att_weight: Attention weights used to reconstruct z
        """
        # Compute cosine similarity between x and memory items
        att_weight = F.linear(x, self.weight)  # (B, M)
        att_weight = F.softmax(att_weight, dim=1) # (B, M)
        
        # Hard shrinkage: remove small attention weights to enforce sparsity
        if self.shrink_thres > 0:
            att_weight = self._hard_shrink(att_weight)
            # Re-normalize
            att_weight = F.normalize(att_weight, p=1, dim=1)

        # Reconstruct z from memory
        z_hat = F.linear(att_weight, self.weight.t())
        return z_hat, att_weight

    def _hard_shrink(self, x):
        return F.relu(x - self.shrink_thres) * x


class MemAE(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=128, mem_dim=50):
        """
        Memory-Augmented Autoencoder for Anomaly Detection.
        Instead of decoding directly from the encoder's latent space (which might 
        allow the model to perfectly reconstruct novel anomalies), we force the 
        latent vector to be reconstructed using a convex combination of normal 
        "Memory Prototypes" before decoding.
        
        If an anomalous input arrives, it won't match any memory prototypes well,
        leading to a high reconstruction error.
        """
        super(MemAE, self).__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, hidden_dim)
        )
        
        # Memory
        self.memory = MemoryModule(mem_dim=mem_dim, fea_dim=hidden_dim)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, input_dim)
        )

    def forward(self, x):
        # 1. Encode
        z = self.encoder(x)
        
        # 2. Reconstruct z using Memory Prototypes
        z_hat, att_weight = self.memory(z)
        
        # 3. Decode
        x_hat = self.decoder(z_hat)
        
        return x_hat, att_weight

    def compute_anomaly_score(self, x):
        """
        Computes the reconstruction error (MSE) as the anomaly score.
        High error = Open-Set Anomaly.
        """
        self.eval()
        with torch.no_grad():
            x_hat, _ = self.forward(x)
            # Compute MSE loss per item in batch
            error = torch.mean((x - x_hat) ** 2, dim=1)
            return error
