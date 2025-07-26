"""Knowledge graph data models using Pydantic for validation."""

from typing import List
from pydantic import BaseModel, Field


class KnowledgeNode(BaseModel):
    """Represents a single concept in the knowledge graph.
    
    This model follows Google ADK patterns for data validation
    and immutability through Pydantic.
    """
    
    id: str = Field(
        description="A unique, machine-readable identifier (e.g., 'dqn', 'probability_theory')"
    )
    label: str = Field(
        description="The human-readable name of the concept (e.g., 'Deep Q-Network')"
    )
    domain: str = Field(
        description="The primary knowledge domain (e.g., 'Reinforcement Learning', 'Statistics')"
    )
    
    class Config:
        """Pydantic configuration for the model."""
        frozen = True  # Make the model immutable
        str_strip_whitespace = True
        validate_assignment = True


class KnowledgeEdge(BaseModel):
    """Represents a prerequisite relationship between two concepts.
    
    Follows the directed graph pattern where source is a prerequisite of target.
    """
    
    source: str = Field(
        description="The ID of the prerequisite node."
    )
    target: str = Field(
        description="The ID of the node that requires the source."
    )
    type: str = Field(
        default="PREREQUISITE",
        description="The type of relationship, should be 'PREREQUISITE'."
    )
    
    class Config:
        """Pydantic configuration for the model."""
        frozen = True
        str_strip_whitespace = True
        validate_assignment = True


class KnowledgeGraph(BaseModel):
    """The complete structured representation of a knowledge graph.
    
    This is the main aggregate model that contains all nodes and edges
    for a specific topic area.
    """
    
    topic: str = Field(
        description="The central topic of this graph, e.g., 'Reinforcement Learning'."
    )
    nodes: List[KnowledgeNode] = Field(
        description="A list of all identified knowledge concepts.",
        default_factory=list
    )
    edges: List[KnowledgeEdge] = Field(
        description="A list of all prerequisite relationships.",
        default_factory=list
    )
    
    class Config:
        """Pydantic configuration for the model."""
        frozen = True
        str_strip_whitespace = True
        validate_assignment = True
    
    def get_node_count(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self.nodes)
    
    def get_edge_count(self) -> int:
        """Get the number of edges in the graph."""
        return len(self.edges)
    
    def get_node_by_id(self, node_id: str) -> KnowledgeNode | None:
        """Find a node by its ID.
        
        Args:
            node_id: The ID to search for.
            
        Returns:
            The node if found, None otherwise.
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def validate_graph_integrity(self) -> List[str]:
        """Validate that all edge references point to existing nodes.
        
        Returns:
            List of validation errors, empty if valid.
        """
        errors = []
        node_ids = {node.id for node in self.nodes}
        
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge references non-existent source node: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"Edge references non-existent target node: {edge.target}")
        
        return errors 