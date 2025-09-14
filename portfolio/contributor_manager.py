"""Contributor Management Module.

This module handles all contributor-related operations including:
- Managing contributor information (names, emails)
- Loading and saving contributor data
- Validation and data integrity

This module follows the single responsibility principle and separates
business logic from UI concerns.
"""

import logging
import pandas as pd
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from data.repositories.base_repository import BaseRepository
from display.console_output import print_success, print_error, print_warning, print_info

logger = logging.getLogger(__name__)


class ContributorManager:
    """Manages contributor information and operations."""
    
    def __init__(self, repository: BaseRepository):
        """Initialize the contributor manager.
        
        Args:
            repository: Repository for data access
        """
        self.repository = repository
        self.fund_file = Path(repository.data_dir) / "fund_contributions.csv"
        logger.info("Contributor manager initialized")
    
    def get_contributors(self) -> pd.DataFrame:
        """Get all unique contributors with their information.
        
        Returns:
            DataFrame with columns: Contributor, Email
            
        Raises:
            FileNotFoundError: If fund contributions file doesn't exist
        """
        if not self.fund_file.exists():
            raise FileNotFoundError("No fund contributions file found")
        
        # Read existing data
        df = pd.read_csv(self.fund_file)
        
        # Ensure Email column exists for backward compatibility
        if 'Email' not in df.columns:
            df['Email'] = ''
        
        # Get unique contributors
        contributors = df[['Contributor', 'Email']].groupby('Contributor').agg({'Email': 'first'}).reset_index()
        contributors = contributors.sort_values('Contributor')
        
        return contributors
    
    def update_contributor(self, old_name: str, new_name: str, new_email: str) -> bool:
        """Update contributor information.
        
        Args:
            old_name: Current contributor name
            new_name: New contributor name
            new_email: New contributor email
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.fund_file.exists():
                print_error("No fund contributions file found")
                return False
            
            # Read existing data
            df = pd.read_csv(self.fund_file)
            
            # Ensure Email column exists
            if 'Email' not in df.columns:
                df['Email'] = ''
            
            # Update the DataFrame
            df.loc[df['Contributor'] == old_name, 'Contributor'] = new_name
            df.loc[df['Contributor'] == new_name, 'Email'] = new_email
            
            # Save updated CSV
            df.to_csv(self.fund_file, index=False)
            logger.info(f"Updated contributor: {old_name} → {new_name}, email: {new_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating contributor: {e}")
            print_error(f"Failed to update contributor: {e}")
            return False
    
    def validate_email(self, email: str) -> bool:
        """Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not email:
            return True  # Empty email is okay
        
        return '@' in email and '.' in email.split('@')[1]
    
    def save_contribution(self, contribution_data: Dict[str, Any]) -> bool:
        """Save contribution data to CSV file.
        
        Args:
            contribution_data: Dictionary containing contribution information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create DataFrame with new contribution
            new_df = pd.DataFrame([contribution_data])
            
            # Append to existing file or create new one
            if self.fund_file.exists():
                existing_df = pd.read_csv(self.fund_file)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df
            
            # Save to CSV
            combined_df.to_csv(self.fund_file, index=False)
            logger.info(f"Contribution saved to {self.fund_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving contribution: {e}")
            return False


class ContributorUI:
    """Handles UI interactions for contributor management."""
    
    def __init__(self, contributor_manager: ContributorManager):
        """Initialize the contributor UI.
        
        Args:
            contributor_manager: ContributorManager instance
        """
        self.manager = contributor_manager
    
    def manage_contributors_interactive(self) -> bool:
        """Interactive contributor management interface.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Manage Contributors", "👥")
            
            # Get contributors
            try:
                contributors = self.manager.get_contributors()
            except FileNotFoundError:
                print_warning("No fund contributions file found")
                return False
            
            if contributors.empty:
                print_warning("No contributors found")
                return False
            
            # Loop until user exits
            while True:
                # Refresh contributors list each iteration in case changes were made
                try:
                    contributors = self.manager.get_contributors()
                except FileNotFoundError:
                    print_warning("No fund contributions file found")
                    return False
                
                if contributors.empty:
                    print_warning("No contributors found")
                    return False
                
                # Display contributors
                self._display_contributors(contributors)
                
                # Get user selection
                selected_contributor = self._get_contributor_selection(contributors)
                if selected_contributor is None:
                    print_info("Exiting contributor management")
                    return True
                
                # Get updated information
                current_name = selected_contributor['Contributor']
                current_email = selected_contributor['Email'] if pd.notna(selected_contributor['Email']) else ""
                
                new_name, new_email = self._get_updated_info(current_name, current_email)
                
                # Check if changes were made
                if new_name == current_name and new_email == current_email:
                    print_info("No changes made")
                    continue  # Continue loop instead of returning
                
                # Confirm changes
                if not self._confirm_changes(current_name, current_email, new_name, new_email):
                    print_info("Changes cancelled")
                    continue  # Continue loop instead of returning
                
                # Update contributor
                success = self.manager.update_contributor(current_name, new_name, new_email)
                if success:
                    print_success("Contributor information updated successfully")
                    print()  # Add spacing before next iteration
                else:
                    print_error("Failed to update contributor")
            
        except KeyboardInterrupt:
            print_info("\nContributor management cancelled by user")
            return True
        except Exception as e:
            logger.error(f"Error in interactive contributor management: {e}")
            print_error(f"Failed to manage contributors: {e}")
            return False
    
    def _display_contributors(self, contributors: pd.DataFrame) -> None:
        """Display contributors in a formatted table."""
        print("Current Contributors:")
        print("─" * 60)
        print(f"{'#':<3} {'Name':<25} {'Email':<30}")
        print("─" * 60)
        
        for i, row in contributors.iterrows():
            idx = i + 1
            name = row['Contributor']
            email = row['Email'] if row['Email'] and pd.notna(row['Email']) else "Not provided"
            print(f"{idx:<3} {name:<25} {email:<30}")
        
        print("─" * 60)
        print("Select a contributor by number to edit, or press Enter to exit")
    
    def _get_contributor_selection(self, contributors: pd.DataFrame) -> Optional[pd.Series]:
        """Get user selection for contributor to edit.
        
        Args:
            contributors: DataFrame of contributors
            
        Returns:
            Selected contributor series or None if exiting
        """
        while True:
            try:
                selection = input("Enter selection: ").strip()
                
                # Exit if empty input
                if not selection:
                    return None
                
                selection_lower = selection.lower()
                if selection_lower == 'cancel':
                    return None
                
                selection_num = int(selection)
                if 1 <= selection_num <= len(contributors):
                    return contributors.iloc[selection_num - 1]
                else:
                    print_error(f"Invalid selection. Please enter a number between 1 and {len(contributors)}")
                    
            except ValueError:
                print_error("Invalid input. Please enter a number or press Enter to exit")
    
    def _get_updated_info(self, current_name: str, current_email: str) -> Tuple[str, str]:
        """Get updated contributor information from user.
        
        Args:
            current_name: Current contributor name
            current_email: Current contributor email
            
        Returns:
            Tuple of (new_name, new_email)
        """
        print(f"\nEditing contributor: {current_name}")
        print(f"Current email: {current_email if current_email else 'Not provided'}")
        
        # Get new name
        new_name = input(f"Enter new name [{current_name}]: ").strip()
        if not new_name:
            new_name = current_name
        
        # Get new email
        new_email = input(f"Enter new email [{current_email}]: ").strip()
        if not new_email:
            new_email = current_email
        
        # Validate email format if provided
        if new_email and not self.manager.validate_email(new_email):
            print_warning("Email format may be invalid, but continuing...")
        
        return new_name, new_email
    
    def _confirm_changes(self, current_name: str, current_email: str, 
                        new_name: str, new_email: str) -> bool:
        """Confirm changes with the user.
        
        Args:
            current_name: Current contributor name
            current_email: Current contributor email  
            new_name: New contributor name
            new_email: New contributor email
            
        Returns:
            bool: True if confirmed, False otherwise
        """
        print(f"\nChanges to be made:")
        if new_name != current_name:
            print(f"  Name: {current_name} → {new_name}")
        if new_email != current_email:
            print(f"  Email: {current_email if current_email else '(empty)'} → {new_email if new_email else '(empty)'}")
        
        confirm = input("\nSave changes? (Y/n): ").strip().lower()
        # Default to Yes - only return False if explicitly 'n' or 'no'
        return confirm not in ['n', 'no']
