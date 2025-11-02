import logging

from data_classes import PermissionSet, JaccardDifference


class DuplicateFinder:

    SIMILARITY_THRESHOLD = 0.9

    def __init__(self, permsets: list[PermissionSet]) -> None:
        self.permsets = permsets

    def jaccard(self) -> list[JaccardDifference]:
        logging.debug(">> jaccard")
        duplicates:list[JaccardDifference] = []
        nb_permsets = len(self.permsets)
        for i in range(nb_permsets):
            perms_i = set(self.permsets[i].get_all_perms())
            for j in range(i + 1, nb_permsets):
                perms_j = set(self.permsets[j].get_all_perms())
                intersection = perms_i.intersection(perms_j)
                union = perms_i.union(perms_j)
                if union:  # Avoid division by zero
                    similarity = len(intersection) / len(union)
                    if similarity >= DuplicateFinder.SIMILARITY_THRESHOLD:
                        duplicates.append(JaccardDifference(self.permsets[i], self.permsets[j], similarity))
                if not union and not intersection:
                    # Both permission sets are empty, consider them identical
                    duplicates.append(JaccardDifference(self.permsets[i], self.permsets[j], 1.0))
        logging.debug(f"<< jaccard: returning nb records={len(duplicates)}")
        # Sort by similarity descending (most similar first)
        duplicates = sorted(duplicates, key=lambda t: t.similarity, reverse=True)
        return duplicates
