import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

export default function ProfilePage() {
  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-light text-[#5a5c69] mb-6">User Profile</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Profile Picture Card */}
        <div className="md:col-span-1">
          <Card className="flex flex-col items-center p-6 text-center">
             <div className="h-24 w-24 rounded-full bg-gray-200 flex items-center justify-center text-4xl mb-4">
               👤
             </div>
             <h3 className="font-bold text-gray-700">Abhishek Rai</h3>
             <p className="text-sm text-gray-500 mb-4">Admin User</p>
             <Button variant="primary" size="sm">Upload New Photo</Button>
          </Card>
        </div>

        {/* Settings Form */}
        <div className="md:col-span-2">
          <Card>
            <h3 className="font-bold text-[#4e73df] mb-4 text-sm uppercase">Account Details</h3>
            <form className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label="First Name" defaultValue="Abhishek" />
                <Input label="Last Name" defaultValue="Rai" />
              </div>
              <Input label="Email Address" defaultValue="name@example.com" type="email" />
              <Input label="Phone Number" placeholder="+1 (555) ..." />
              
              <div className="pt-4 flex justify-end">
                <Button variant="success">Save Changes</Button>
              </div>
            </form>
          </Card>
        </div>

      </div>
    </div>
  );
}