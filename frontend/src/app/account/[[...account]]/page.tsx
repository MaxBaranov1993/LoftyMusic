import { UserProfile } from "@clerk/nextjs";

export default function AccountPage() {
  return (
    <div className="flex justify-center py-8">
      <UserProfile
        appearance={{
          elements: {
            rootBox: "w-full max-w-4xl",
            card: "bg-[#121212] border border-[#282828] shadow-xl rounded-xl",
            navbar: "bg-[#121212] border-r border-[#282828]",
            navbarButton: "text-[#b3b3b3] hover:text-white hover:bg-[#282828]",
            pageScrollBox: "bg-[#121212]",
            profileSection: "border-b border-[#282828]",
            profileSectionTitleText: "text-white",
            profileSectionPrimaryButton: "text-[#1DB954] hover:text-[#1ed760]",
            headerTitle: "text-white",
            headerSubtitle: "text-[#b3b3b3]",
            formFieldLabel: "text-[#b3b3b3]",
            formFieldInput: "bg-[#282828] border-[#282828] text-white",
            formButtonPrimary: "bg-[#1DB954] hover:bg-[#1ed760] text-black",
            badge: "text-[#1DB954] border-[#1DB954]",
            menuButton: "text-[#b3b3b3] hover:text-white",
            menuList: "bg-[#181818] border-[#282828]",
            menuItem: "text-white hover:bg-[#282828]",
          },
        }}
      />
    </div>
  );
}
