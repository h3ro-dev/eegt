"""Train-only unsupervised models; neutral integer outputs, no semantics."""
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from .signal import features


class Tokenizer:
    def __init__(self, method, k, seed):
        self.method, self.k, self.seed = method, k, seed
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=20, svd_solver="full") if method == "waveform" else None
        self.clusterer = KMeans(n_clusters=k, init="k-means++", n_init=1, max_iter=200,
                                random_state=seed, algorithm="lloyd")

    def fit(self, train_waves):
        f = self.scaler.fit_transform(features(train_waves, self.method))
        if self.pca is not None:
            f = self.pca.fit_transform(f)
        self.clusterer.fit(f)
        distances = self.clusterer.transform(f).min(axis=1)
        self.ood_threshold = float(np.quantile(distances, .99))
        return self

    def predict(self, waves):
        f = self.scaler.transform(features(waves, self.method))
        if self.pca is not None:
            f = self.pca.transform(f)
        distances = self.clusterer.transform(f)
        labels = distances.argmin(axis=1)
        closest = distances[np.arange(len(labels)), labels]
        return labels, closest <= self.ood_threshold, closest

    def export_arrays(self):
        out = dict(scale_mean=self.scaler.mean_, scale_std=self.scaler.scale_,
                   centroids=self.clusterer.cluster_centers_, threshold=np.array(self.ood_threshold))
        if self.pca is not None:
            out.update(pca_mean=self.pca.mean_, pca_components=self.pca.components_)
        return out
